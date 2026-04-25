from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileListItem(BaseModel):
    uuid: str
    name: str
    size: int
    mime_type: str
    extension: str
    uploaded_at: datetime

class FileListResponse(BaseModel):
    total: int
    files: list[FileListItem]

class FileUploadResponse(BaseModel):
    uuid: str
    name: str
    size: int
    uploaded_at: datetime

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str