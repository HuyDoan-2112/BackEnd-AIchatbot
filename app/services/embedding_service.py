from typing import List, Union
from app.schemas.embedding import (
    EmbeddingRequest,
    EmbeddingResponse,
)


class EmbeddingService:
    
    def __init__(self, embedding_repository):
        self.embedding_repository = embedding_repository
    
    async def create_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        pass
    
    async def parse_input(self, input_data: Union[str, List[str], List[int], List[List[int]]]) -> List[str]:
        pass
    
    async def encode_base64(self, embedding: List[float]) -> str:
        pass
    
    async def count_tokens(self, texts: List[str], model: str) -> int:
        pass


embedding_service = EmbeddingService(embedding_repository=None)
