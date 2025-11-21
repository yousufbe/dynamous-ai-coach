from __future__ import annotations

from pathlib import Path

from src.rag_pipeline.embeddings.local_client import SentenceTransformerEmbeddingClient
from src.rag_pipeline.embeddings.manifest import ArtifactManifest
from src.rag_pipeline.schemas import ChunkData, ChunkMetadata


class StubModel:
    def __init__(self) -> None:
        self.batch_size: int | None = None

    def encode(
        self,
        sentences,
        *,
        batch_size=None,
        convert_to_numpy=True,
        normalize_embeddings=None,
    ):
        self.batch_size = batch_size
        return [[float(len(text)), float(len(text) + 1)] for text in sentences]

    def get_sentence_embedding_dimension(self) -> int:
        return 2


def test_sentence_transformer_client_embeds_texts_and_chunks(tmp_path: Path) -> None:
    manifest = ArtifactManifest(
        version="v1",
        base_model="base",
        dataset_fingerprint="fp",
        train_pair_count=1,
        validation_pair_count=1,
        embedding_dimension=2,
        hyperparameters={"epochs": 1},
        commit_hash="deadbeef",
        created_at="2024-01-01T00:00:00Z",
    )
    stub = StubModel()
    client = SentenceTransformerEmbeddingClient(
        model_path=tmp_path,
        batch_size=2,
        model_label="ft-model",
        manifest=manifest,
        model_loader=lambda _: stub,
    )
    texts_response = client.embed_texts(["hello", "world"])
    assert len(texts_response.embeddings) == 2
    assert texts_response.embeddings[0].model == "ft-model"
    assert stub.batch_size == 2
    assert client.model_info.dataset_fingerprint == "fp"

    chunk = ChunkData(
        text="chunk",
        metadata=ChunkMetadata(
            page_number=1,
            chunk_index=0,
            section_heading=None,
            structural_type="paragraph",
        ),
        character_count=5,
    )
    chunk_embeddings = client.embed_document_chunks([chunk])
    assert chunk_embeddings[0].vector[0] == 5.0
