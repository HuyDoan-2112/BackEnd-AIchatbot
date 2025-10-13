import hashlib 
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    page_content: str
    metadata: dict

class DocumentModel(BaseModel):
    page_content: str
    metadata: Optional[dict] = {}

    def generate_digest(self) -> str:
        """Generate a SHA256 digest of the document content."""
        # Check if page_content is not None, then update the digest
        return hashlib.sha256(self.page_content.encode('utf-8')).hexdigest()