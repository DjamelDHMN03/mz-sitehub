from fastapi import APIRouter, status, HTTPException
from schemas.document import DocumentCreate, DocumentResponse
from typing import List
from datetime import datetime

router = APIRouter(prefix="/documents", tags=["Documents Management"])

fake_docs_db = []

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(doc: DocumentCreate):
    new_doc = doc.dict()
    new_doc["id"] = len(fake_docs_db) + 1
    new_doc["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fake_docs_db.append(new_doc)
    return new_doc

@router.get("/", response_model=List[DocumentResponse])
def get_documents():
    return fake_docs_db

@router.get("/site/{site_id}", response_model=List[DocumentResponse])
def get_documents_by_site(site_id: str):
    return [d for d in fake_docs_db if d["site_id"] == site_id]
