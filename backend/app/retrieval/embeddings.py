from typing import Protocol, Sequence

import httpx


class EmbeddingProvider(Protocol):
    provider: str
    model: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    provider = "openai"

    def __init__(self, api_key: str, model: str, dimension: int, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key, self.model, self.dimension, self.base_url = api_key, model, dimension, base_url.rstrip("/")

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = httpx.post(f"{self.base_url}/embeddings", headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": list(texts), "dimensions": self.dimension}, timeout=60.0)
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in data]
