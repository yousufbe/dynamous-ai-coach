"""Command-line interface for Docling ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.pipeline import run_ingestion_job
from src.rag_pipeline.schemas import (
    IngestionRequest,
    IngestionResult,
    SourceIngestionStatus,
)
from src.rag_pipeline.runtime import cleanup_runtime, create_pipeline_runtime
from src.shared.logging import get_logger


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Docling ingestion pipeline CLI.")
    parser.add_argument(
        "--source-dir",
        dest="source_dirs",
        action="append",
        help="Override configured source directories (can be provided multiple times).",
    )
    parser.add_argument(
        "--force-reingest",
        action="store_true",
        help="Reprocess all documents regardless of stored hashes.",
    )
    parser.add_argument(
        "--pipeline-id",
        help="Override the pipeline identifier used in logs and metrics.",
    )
    parser.add_argument(
        "--glob",
        dest="globs",
        action="append",
        help="Glob pattern applied within source directories (default: **/*).",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Optional KEY=VALUE file used to populate environment variables before loading config.",
    )
    parser.add_argument(
        "--output-format",
        choices=("text", "json"),
        default="text",
        help="Select structured JSON output or human-readable text summary.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display CLI version information and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.version:
        print(_detect_version())
        return 0

    if args.config_file:
        _load_env_file(args.config_file)

    config = get_rag_ingestion_config()
    request = IngestionRequest()
    if args.source_dirs:
        request.source_directories = args.source_dirs
    if args.globs:
        request.document_glob_patterns = args.globs
    request.force_reingest = args.force_reingest
    request.pipeline_id = args.pipeline_id

    directories_to_validate = (
        [Path(entry).expanduser() for entry in args.source_dirs]
        if args.source_dirs
        else config.source_directories
    )
    missing_dirs = [str(path) for path in directories_to_validate if not path.exists()]
    if missing_dirs:
        print(f"Configured directories do not exist: {', '.join(missing_dirs)}", file=sys.stderr)
        return 2

    try:
        services, embedding_client, db_client = create_pipeline_runtime(config)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to initialize services: {exc}", file=sys.stderr)
        return 2

    try:
        result = run_ingestion_job(
            request=request,
            config=config,
            services=services,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        cleanup_runtime(embedding_client, db_client)
        return 2
    except Exception as exc:  # noqa: BLE001
        get_logger(__name__).exception("cli_ingestion_failed", error=str(exc))
        cleanup_runtime(embedding_client, db_client)
        return 1

    cleanup_runtime(embedding_client, db_client)
    _render_output(result=result, output_format=args.output_format)
    return 0 if result.stats.documents_failed == 0 else 1


def _render_output(result: IngestionResult, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result.model_dump(), indent=2, sort_keys=True))
        return
    print(f"Pipeline: {result.pipeline_id}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(
        "Documents - discovered: {disc}, ingested: {ing}, failed: {fail}".format(
            disc=result.stats.documents_discovered,
            ing=result.stats.documents_ingested,
            fail=result.stats.documents_failed,
        ),
    )
    print(f"Chunks created: {result.stats.chunks_created}")
    failed = [doc for doc in result.documents if doc.status != SourceIngestionStatus.INGESTED]
    if failed:
        print("Failed documents:")
        for doc in failed:
            print(f" - {doc.location}: {doc.error}")


def _detect_version() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()
    except Exception:  # noqa: BLE001
        commit = "unknown"
    return f"Docling Ingestion CLI (commit {commit})"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip()


if __name__ == "__main__":
    raise SystemExit(main())
