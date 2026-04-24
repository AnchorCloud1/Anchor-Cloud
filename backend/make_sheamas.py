content = """import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator, ConfigDict

class RegisterRequest(BaseModel):
    name: str
    identifier: str
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v):
        return v.strip().lower() if "@" in v else v.strip()

class LoginRequest(BaseModel):
    identifier: str
    password: str

class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    plan: str

class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    plan: str
    created_at: datetime
    last_login: Optional[datetime] = None

class FileUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: str
    name: str
    size: int
    mime_type: str
    extension: Optional[str] = None
    encryption_algo: str
    is_encrypted: bool
    message_id: Optional[str] = None
    uploaded_at: datetime

class FileListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: str
    name: str
    size: int
    mime_type: str
    extension: Optional[str] = None
    encryption_algo: str
    is_encrypted: bool
    uploaded_at: datetime

class FileListResponse(BaseModel):
    total: int
    files: List[FileListItem]

class FileDeleteResponse(BaseModel):
    detail: str
    uuid: str

class VaultMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    message_type: str
    payload_summary: Optional[str] = None
    file_uuid: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime

class VaultMessageListResponse(BaseModel):
    total: int
    messages: List[VaultMessageOut]

class HealthResponse(BaseModel):
    status: str
    version: str
    db: str

class ErrorResponse(BaseModel):
    detail: str
"""

with open("schemas.py", "w") as f:
    f.write(content)

print("schemas.py created successfully!")