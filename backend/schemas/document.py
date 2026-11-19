from pydantic import BaseModel
from typing import Optional

class DocumentBase(BaseModel):
    title: str
    site_id: str
    doc_type: str  # ex: "Permit", "Civil Works Report", "Photo"
    file_path: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    uploaded_at: str

    class Config:
        from_attributes = True
