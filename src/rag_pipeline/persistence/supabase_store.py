"""Supabase/PostgreSQL persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, ContextManager, Mapping, MutableMapping, Protocol, Sequence, TypeVar
from uuid import uuid4

try:  # pragma: no cover - optional dependency
    import psycopg
    from psycopg import Connection
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None  # type: ignore
    Connection = Any  # type: ignore
    dict_row = None  # type: ignore

from src.rag_pipeline.config import RagIngestionConfig
from src.rag_pipeline.schemas import (
    ChunkRecord,
    DocumentInput,
    JSONValue,
    SourceIngestionStatus,
)
from src.shared.logging import LoggerProtocol, get_logger

logger: LoggerProtocol = get_logger(__name__)

BatchSQLParams = Sequence[Any] | Mapping[str, Any]
SQLParams = BatchSQLParams | None
T = TypeVar("T")


class DatabaseClientProtocol(Protocol):
    """Protocol describing minimal DB operations needed by the store."""

    def execute(self, query: str, parameters: SQLParams = None) -> Any:
        """Execute a single statement."""

    def executemany(
        self,
        query: str,
        param_sets: Sequence[BatchSQLParams],
    ) -> Any:
        """Execute a statement for each parameter set."""

    def fetchrow(self, query: str, parameters: SQLParams = None) -> Mapping[str, Any] | None:
        """Fetch the first row of a query."""

    def fetchval(self, query: str, parameters: SQLParams = None) -> Any:
        """Fetch a single scalar value."""

    def transaction(self) -> ContextManager[Any]:
        """Return a context manager that wraps a database transaction."""


class PsycopgDatabaseClient(DatabaseClientProtocol):
    """Lightweight psycopg3 wrapper implementing DatabaseClientProtocol."""

    def __init__(self, dsn: str) -> None:
        if psycopg is None:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "psycopg is required for PsycopgDatabaseClient but is not installed.",
            )
        self._connection: Connection[Any] = psycopg.connect(dsn)  # type: ignore[assignment]
        self._connection.autocommit = True

    def close(self) -> None:
        """Close the underlying psycopg connection."""
        self._connection.close()

    def execute(self, query: str, parameters: SQLParams = None) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(query, parameters)

    def executemany(self, query: str, param_sets: Sequence[BatchSQLParams]) -> None:
        with self._connection.cursor() as cursor:
            cursor.executemany(query, param_sets)

    def fetchrow(self, query: str, parameters: SQLParams = None) -> Mapping[str, Any] | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:  # type: ignore[arg-type]
            cursor.execute(query, parameters)
            return cursor.fetchone()

    def fetchval(self, query: str, parameters: SQLParams = None) -> Any:
        with self._connection.cursor() as cursor:
            cursor.execute(query, parameters)
            row = cursor.fetchone()
            return None if row is None else row[0]

    def transaction(self) -> ContextManager[Any]:
        return self._connection.transaction()


@dataclass(frozen=True, slots=True)
class SourceRow:
    """Application-friendly representation of a ``rag.sources`` row."""

    id: str
    location: str
    document_name: str
    content_hash: str
    status: SourceIngestionStatus
    metadata: dict[str, JSONValue]
    error_message: str | None


class SupabaseStore:
    """Encapsulates Supabase/PostgreSQL interactions for ingestion."""

    def __init__(
        self,
        db: DatabaseClientProtocol,
        config: RagIngestionConfig,
    ) -> None:
        self._db = db
        schema = config.supabase_schema
        self._sources_table = f"{schema}.{config.sources_table}"
        self._chunks_table = f"{schema}.{config.chunks_table}"

    def get_source_by_location(self, location: str) -> SourceRow | None:
        """Return an existing row for the provided path."""
        sql = (
            f"select id, location, document_name, content_hash, status, metadata, error_message "
            f"from {self._sources_table} where location = %s"
        )
        row = self._run_query(
            "fetch_source_by_location",
            lambda: self._db.fetchrow(sql, (location,)),
        )
        return self._map_source_row(row) if row else None

    def upsert_source(
        self,
        document: DocumentInput,
        *,
        status: SourceIngestionStatus,
        embedding_model: str,
    ) -> SourceRow:
        """Insert or update a source row and return the stored record."""
        sql = f"""
            insert into {self._sources_table} (
                location,
                document_name,
                document_type,
                source_type,
                content_hash,
                status,
                metadata,
                embedding_model,
                error_message
            )
            values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, null)
            on conflict (location) do update set
                document_name = excluded.document_name,
                document_type = excluded.document_type,
                source_type = excluded.source_type,
                content_hash = excluded.content_hash,
                status = excluded.status,
                metadata = excluded.metadata,
                embedding_model = excluded.embedding_model,
                error_message = excluded.error_message,
                updated_at = timezone('utc', now())
            returning id,
                      location,
                      document_name,
                      content_hash,
                      status,
                      metadata,
                      error_message
        """
        metadata = _build_source_metadata(document)
        parameters: tuple[Any, ...] = (
            str(document.metadata.location),
            document.display_name,
            document.metadata.document_type,
            document.metadata.source_type.value,
            document.metadata.content_hash,
            status.value,
            json.dumps(metadata),
            embedding_model,
        )
        row = self._run_query(
            "upsert_source",
            lambda: self._db.fetchrow(sql, parameters),
        )
        if row is None:  # pragma: no cover - defensive
            raise RuntimeError("Upsert source did not return a row.")
        return self._map_source_row(row)

    def mark_source_status(
        self,
        *,
        location: str,
        status: SourceIngestionStatus,
        error_message: str | None = None,
    ) -> SourceRow | None:
        """Update `status` and optional error message for a source row."""
        sql = f"""
            update {self._sources_table}
            set status = %s,
                error_message = %s,
                updated_at = timezone('utc', now())
            where location = %s
            returning id,
                      location,
                      document_name,
                      content_hash,
                      status,
                      metadata,
                      error_message
        """
        row = self._run_query(
            "mark_source_status",
            lambda: self._db.fetchrow(sql, (status.value, error_message, location)),
        )
        return self._map_source_row(row) if row else None

    def mark_source_failed(self, location: str, message: str) -> SourceRow | None:
        """Convenience helper that marks a document as failed."""
        return self.mark_source_status(
            location=location,
            status=SourceIngestionStatus.FAILED,
            error_message=message,
        )

    def replace_chunks_for_source(
        self,
        *,
        source_id: str,
        chunk_records: Sequence[ChunkRecord],
    ) -> None:
        """Replace all chunks for the given source id atomically."""
        delete_sql = f"delete from {self._chunks_table} where source_id = %s"
        insert_sql = f"""
            insert into {self._chunks_table} (
                source_id,
                chunk_index,
                page_number,
                structural_type,
                section_heading,
                text,
                embedding,
                embedding_model,
                metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """
        param_sets: list[tuple[Any, ...]] = [
            (
                source_id,
                record.chunk_index,
                _safe_int(record.metadata.get("page_number")),
                _safe_str(record.metadata.get("structural_type")),
                _safe_str(record.metadata.get("section_heading")),
                record.text,
                list(record.embedding),
                record.embedding_model,
                _serialize_chunk_metadata(record),
            )
            for record in chunk_records
        ]
        with self._db.transaction():
            self._run_query(
                "delete_chunks_for_source",
                lambda: self._db.execute(delete_sql, (source_id,)),
            )
            if param_sets:
                self._run_query(
                    "insert_chunks_for_source",
                    lambda: self._db.executemany(insert_sql, param_sets),
                )

    def delete_chunks_for_source(self, source_id: str) -> None:
        """Delete all chunk rows for a source without inserting new ones."""
        sql = f"delete from {self._chunks_table} where source_id = %s"
        self._run_query(
            "delete_chunks_for_source",
            lambda: self._db.execute(sql, (source_id,)),
        )

    @staticmethod
    def has_content_changed(
        document: DocumentInput,
        existing: SourceRow | None,
    ) -> bool:
        """Return True if the document should be re-ingested."""
        if existing is None:
            return True
        return document.metadata.content_hash != existing.content_hash

    def _map_source_row(self, row: Mapping[str, Any] | None) -> SourceRow:
        if row is None:  # pragma: no cover - defensive
            raise ValueError("Cannot map empty row.")
        metadata_value = row.get("metadata", {}) or {}
        metadata: dict[str, JSONValue]
        if isinstance(metadata_value, str):
            metadata = json.loads(metadata_value)
        else:
            metadata = dict(metadata_value)
        return SourceRow(
            id=str(row["id"]),
            location=str(row["location"]),
            document_name=str(row.get("document_name", "")),
            content_hash=str(row["content_hash"]),
            status=SourceIngestionStatus(row["status"]),
            metadata=metadata,
            error_message=row.get("error_message"),
        )

    def _run_query(self, name: str, func: Callable[[], T]) -> T:
        start = perf_counter()
        logger.info("db_query_started", operation=name)
        try:
            result = func()
        except Exception:
            logger.exception("db_query_failed", operation=name)
            raise
        duration_ms = (perf_counter() - start) * 1000.0
        logger.info(
            "db_query_completed",
            operation=name,
            duration_ms=duration_ms,
        )
        return result


class InMemoryStore:
    """Fallback store for tests that need deterministic behaviour."""

    def __init__(self) -> None:
        self.sources: MutableMapping[str, SourceRow] = {}
        self.chunks: MutableMapping[str, list[ChunkRecord]] = {}

    def get_source_by_location(self, location: str) -> SourceRow | None:
        return self.sources.get(location)

    def upsert_source(
        self,
        document: DocumentInput,
        *,
        status: SourceIngestionStatus,
        embedding_model: str,
    ) -> SourceRow:
        existing = self.sources.get(str(document.metadata.location))
        row = SourceRow(
            id=existing.id if existing else uuid4().hex,
            location=str(document.metadata.location),
            document_name=document.display_name,
            content_hash=document.metadata.content_hash,
            status=status,
            metadata=_build_source_metadata(document),
            error_message=None,
        )
        self.sources[row.location] = row
        return row

    def mark_source_status(
        self,
        *,
        location: str,
        status: SourceIngestionStatus,
        error_message: str | None = None,
    ) -> SourceRow | None:
        row = self.sources.get(location)
        if row is None:
            return None
        updated = SourceRow(
            id=row.id,
            location=row.location,
            document_name=row.document_name,
            content_hash=row.content_hash,
            status=status,
            metadata=row.metadata,
            error_message=error_message,
        )
        self.sources[location] = updated
        return updated

    def mark_source_failed(self, location: str, message: str) -> SourceRow | None:
        return self.mark_source_status(location=location, status=SourceIngestionStatus.FAILED, error_message=message)

    def replace_chunks_for_source(
        self,
        *,
        source_id: str,
        chunk_records: Sequence[ChunkRecord],
    ) -> None:
        self.chunks[source_id] = list(chunk_records)

    def delete_chunks_for_source(self, source_id: str) -> None:
        self.chunks.pop(source_id, None)

    @staticmethod
    def has_content_changed(
        document: DocumentInput,
        existing: SourceRow | None,
    ) -> bool:
        return SupabaseStore.has_content_changed(document=document, existing=existing)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _build_source_metadata(document: DocumentInput) -> dict[str, JSONValue]:
    metadata = dict(document.metadata.extra_metadata)
    metadata.update(
        {
            "size_bytes": document.metadata.size_bytes,
            "last_modified": (
                document.metadata.last_modified.isoformat()
                if document.metadata.last_modified
                else None
            ),
            "source_type": document.metadata.source_type.value,
        },
    )
    return metadata


def _serialize_chunk_metadata(record: ChunkRecord) -> str:
    return json.dumps(record.metadata)


class PersistenceStoreProtocol(Protocol):
    """Protocol implemented by SupabaseStore and InMemoryStore."""

    def get_source_by_location(self, location: str) -> SourceRow | None:
        """Return an existing source row."""

    def upsert_source(
        self,
        document: DocumentInput,
        *,
        status: SourceIngestionStatus,
        embedding_model: str,
    ) -> SourceRow:
        """Insert or update a source."""

    def mark_source_status(
        self,
        *,
        location: str,
        status: SourceIngestionStatus,
        error_message: str | None = None,
    ) -> SourceRow | None:
        """Update the source status."""

    def mark_source_failed(self, location: str, message: str) -> SourceRow | None:
        """Mark a source as failed."""

    def replace_chunks_for_source(
        self,
        *,
        source_id: str,
        chunk_records: Sequence[ChunkRecord],
    ) -> None:
        """Replace chunk rows for a source."""

    def delete_chunks_for_source(self, source_id: str) -> None:
        """Delete chunks for a source."""

    def has_content_changed(
        self,
        document: DocumentInput,
        existing: SourceRow | None,
    ) -> bool:
        """Return whether a document requires reingestion."""
