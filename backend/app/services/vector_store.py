import os
import faiss
import numpy as np
from typing import List, Tuple
from backend.app.core.config import settings

class VectorStoreManager:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index_path = settings.FAISS_INDEX_PATH
        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> faiss.Index:
        """Loads a FAISS index from disk or creates a new empty one if not found."""
        if os.path.exists(self.index_path):
            try:
                # Load existing index
                return faiss.read_index(str(self.index_path))
            except Exception as e:
                # If loading fails, fallback to creating a new index
                pass
                
        # Create a new index mapping IDs to L2 Flat Index
        flat_index = faiss.IndexFlatL2(self.dimension)
        return faiss.IndexIDMap(flat_index)

    def add_vectors(self, vectors: List[List[float]], ids: List[int]) -> None:
        """
        Adds vectors to the index with associated database IDs.
        
        Args:
            vectors: List of float lists (embeddings)
            ids: List of database chunk IDs corresponding to the embeddings
        """
        if not vectors or not ids:
            return
            
        np_vectors = np.array(vectors, dtype=np.float32)
        np_ids = np.array(ids, dtype=np.int64)
        
        self.index.add_with_ids(np_vectors, np_ids)
        self.save_index()

    def save_index(self) -> None:
        """Persists the FAISS index to disk."""
        # Ensure directory exists
        settings.create_directories()
        faiss.write_index(self.index, str(self.index_path))

    def search(self, query_vector: List[float], k: int = 5) -> List[Tuple[int, float]]:
        """
        Performs L2 search in FAISS and returns matching IDs and distances.
        
        Args:
            query_vector: Embedding vector of the query.
            k: Number of nearest neighbors to retrieve.
            
        Returns:
            List of tuples (chunk_id, distance).
        """
        if self.index.ntotal == 0:
            return []
            
        np_query = np.array([query_vector], dtype=np.float32)
        distances, ids = self.index.search(np_query, k)
        
        results: List[Tuple[int, float]] = []
        for dist, chunk_id in zip(distances[0], ids[0]):
            if chunk_id != -1:  # -1 represents no match found
                results.append((int(chunk_id), float(dist)))
                
        return results

    def clear_index(self) -> None:
        """Clears all vectors from the index and saves it."""
        flat_index = faiss.IndexFlatL2(self.dimension)
        self.index = faiss.IndexIDMap(flat_index)
        self.save_index()
