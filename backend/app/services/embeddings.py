import logging
from functools import lru_cache

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def get_embedding_model():
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))
