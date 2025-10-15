from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from fastapi import UploadFile
import re, os, io, hashlib
from datetime import datetime
import uuid

ALLOWED_EXTS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

def sniff_magic(header: bytes, ext: str) -> bool:
    if ext == ".pdf":
        return header.startswith(b"%PDF-")
    if ext in (".png",):
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return header.startswith(b"\xff\xd8")
    if ext == ".gif":  # if you later allow .gif
        return header.startswith(b"GIF8")
    if ext in (".docx", ".xlsx", ".pptx"):
        return header.startswith(b"PK\x03\x04")
    return True

MAX_FILES = 12
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_TOTAL_SIZE = 80 * 1024 * 1024

class ProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100, default="New Project")
    description: Optional[str] = Field(default=None, max_length=500)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    is_public: bool = Field(default=False)
    files: List[UploadFile] = Field(default_factory=list)
    member_ids: List[uuid.UUID] = Field(default_factory=list)
    conversation_ids: List[uuid.UUID] = Field(default_factory=list)
    document_ids: List[uuid.UUID] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        # consider allowing hyphen—common in slugs
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", v):
            raise ValueError("Project name may contain letters, digits, underscore, hyphen, and dot only")
        return v

    @field_validator("files")
    @classmethod
    def validate_files(cls, uploads: List[UploadFile]) -> List[UploadFile]:
        if len(uploads) > MAX_FILES:
            raise ValueError(f"Too many files (max {MAX_FILES}).")

        total_size = 0
        seen_hashes: set[str] = set()

        for f in uploads:
            filename = os.path.basename(f.filename or "")
            if not filename or filename.startswith("."):
                raise ValueError("Invalid filename.")
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            if ext not in ALLOWED_EXTS:
                raise ValueError(f"Extension {ext} not allowed.")

          
            fp = f.file
            pos = fp.tell()
            header = fp.read(12)
            fp.seek(0, io.SEEK_END)
            size = fp.tell()
            fp.seek(pos, io.SEEK_SET)

            if size > MAX_FILE_SIZE:
                raise ValueError(f"{filename} is too large (>{MAX_FILE_SIZE//(1024*1024)} MB).")
            total_size += size
            if total_size > MAX_TOTAL_SIZE:
                raise ValueError(f"Total upload size exceeds {(MAX_TOTAL_SIZE//(1024*1024))} MB.")

            if not sniff_magic(header, ext):
                raise ValueError(f"{filename}: signature does not match expected file type.")


            expected_mime = ALLOWED_EXTS[ext]
            if f.content_type and expected_mime not in f.content_type:
                # allow some leeway for text types
                if ext not in (".txt", ".md", ".csv", ".json"):
                    raise ValueError(f"{filename}: unexpected MIME {f.content_type} for {ext}.")

            fp.seek(0)
            h = hashlib.sha256()
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                h.update(chunk)
            file_hash = h.hexdigest()
            fp.seek(0)
            if file_hash in seen_hashes:
                raise ValueError(f"Duplicate file detected: {filename}")
            seen_hashes.add(file_hash)

        return uploads


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
