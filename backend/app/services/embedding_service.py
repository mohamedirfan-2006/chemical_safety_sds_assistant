from typing import List
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

class EmbeddingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to avoid loading the model multiple times."""
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._model = None
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Lazily load the SentenceTransformer model."""
        if self._model is None:
            # This downloads or loads the model from cache
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        return self._model

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of texts.
        
        Args:
            texts: List of strings to embed.
            
        Returns:
            List of float lists (vector representation).
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates dense vector embedding for a single text string.
        
        Args:
            text: String to embed.
            
        Returns:
            List of floats.
        """
        embedding = self.model.encode(text, show_progress_bar=False, convert_to_numpy=True)
        return embedding.tolist()
