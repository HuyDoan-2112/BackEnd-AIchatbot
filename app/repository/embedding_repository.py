from typing import List, Union


class EmbeddingRepository:
    
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key
        self.model_name = model_name
    
    async def create_embeddings(self, texts: Union[str, List[str]], model: str = None, **kwargs) -> List[List[float]]:
        pass
    
    async def count_tokens(self, text: str) -> int:
        pass


embedding_repository = EmbeddingRepository()
