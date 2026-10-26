"""run_indexing.py

Orchestrates: Ingestion -> Chunking -> Indexing.
"""

from qdrant_client import QdrantClient

from chunking.chunker import DocumentChunker
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository
from ingestion.parsers import load_all_documents  # adjust to your parser's function


def main() -> None:
    # 1. Connect to Qdrant
    config = IndexConfig()
    client = QdrantClient(url="http://localhost:6333")
    repo = QdrantHybridRepository(client=client, config=config)

    # 2. Ingest
    print("Loading documents from ingestion...")
    documents = load_all_documents("data/")  # your parsed documents iterable

    # 3. Chunk
    print("Chunking documents...")
    chunker = DocumentChunker(chunk_size=384, chunk_overlap=64)
    chunks = chunker.split_all(documents)

    # 4. Index
    print(f"Initializing collection '{config.collection}'...")
    repo.init_schema(recreate=True)

    print("Embedding and indexing chunks...")
    total_indexed = repo.add_chunks(chunks)
    print(f"Done. Successfully indexed {total_indexed} chunks.")


if __name__ == "__main__":
    main()