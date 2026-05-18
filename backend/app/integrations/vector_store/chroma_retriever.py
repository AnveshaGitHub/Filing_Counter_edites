from __future__ import annotations

from typing import Any


class ChromaRetriever:
    def __init__(
        self, persist_directory: str = "./chroma_db", collection_name: str = "document_chunks"
    ) -> None:
        self.client = None
        self.collection = None

        try:
            import chromadb  # type: ignore
        except Exception:
            return

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def search_document(self, document_id: int, query: str, top_k: int = 5) -> list[dict]:
        if self.collection is None:
            return []

        result = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"document_id": document_id},
            include=["documents", "metadatas", "distances"],
        )

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0] if "ids" in result else [None] * len(docs)

        rows: list[dict[str, Any]] = []
        for idx, text in enumerate(docs):
            meta = metas[idx] if idx < len(metas) else {}
            distance = distances[idx] if idx < len(distances) else None
            rows.append(
                {
                    "chunk_id": ids[idx] if idx < len(ids) else None,
                    "text": text,
                    "page_no": meta.get("page_no"),
                    "score": distance,
                    "metadata": meta,
                }
            )
        return rows
