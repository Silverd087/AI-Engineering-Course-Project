"""run_experiments.py

Runs test queries across the three retrieval strategies and prints comparisons.
"""

from qdrant_client import QdrantClient
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository


def run_benchmark(test_queries: list[str]) -> None:
    config = IndexConfig()
    client = QdrantClient(url="http://localhost:6333")
    repo = QdrantHybridRepository(client=client, config=config)

    modes = ("sparse", "dense", "hybrid")

    for query in test_queries:
        print("=" * 80)
        print(f"QUERY: '{query}'")
        print("=" * 80)

        for mode in modes:
            print(f"\n--- Strategy: {mode.upper()} ---")
            hits = repo.search(query=query, mode=mode, k=3)
            for rank, hit in enumerate(hits, start=1):
                chunk_id = hit.payload.get("chunk_id", "N/A")
                snippet = hit.payload.get("text", "").replace("\n", " ")[:90]
                print(f"  [{rank}] Score: {hit.score:.4f} | ID: {chunk_id} | Text: {snippet}...")


if __name__ == "__main__":
    test_suite = [
        "What is the prerequisite for CS434?",  # Exact code match (favors sparse)
        "How is the course graded?",           # Semantic concept (favors dense)
        "CS434 grading policy and exams",      # Mixed keyword + concept (favors hybrid)
    ]
    run_benchmark(test_suite)