"""
Embeddings provayder — sentence-transformers.
Modellar: bge-large, nomic-embed, all-MiniLM, mxbai-embed.
"""
import asyncio

from ....config import settings

_models: dict[str, object] = {}


def _get_model(model_name: str | None = None):
    name = model_name or settings.EMBEDDING_MODEL
    if name not in _models:
        from sentence_transformers import SentenceTransformer  # lazy import

        _models[name] = SentenceTransformer(name, trust_remote_code=True)
    return _models[name]


async def embed(texts: list[str], model_name: str | None = None) -> list[list[float]]:
    def _run():
        model = _get_model(model_name)
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    return await asyncio.to_thread(_run)
