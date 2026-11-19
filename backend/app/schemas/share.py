import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ShareCreateRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1)
    platform: str | None = Field(None, description="OUTLOOK, WHATSAPP, TELEGRAM ou LIEN")
    expiry_preset: str | None = Field("7d", description="24h, 7d, 30d, custom, ou null pour illimité")
    custom_expiry: datetime | None = None
    recipients: list[str] = Field(default_factory=list)


class ShareFolderRequest(BaseModel):
    """Section 50 : partager tout un dossier par catégories."""
    categories: list[str] = Field(..., min_length=1)
    platform: str | None = None
    expiry_preset: str | None = "7d"
    custom_expiry: datetime | None = None
    recipients: list[str] = Field(default_factory=list)


class ShareLinkOut(BaseModel):
    id: uuid.UUID
    token: str
    share_url: str
    document_ids: list[uuid.UUID]
    platform: str | None
    expires_at: datetime | None
    is_revoked: bool
    download_count: int
    created_at: datetime
    # Liens prêts à l'emploi pour WhatsApp/Telegram/Outlook (section 45-46,
    # jamais envoyés automatiquement — l'utilisateur clique et confirme lui-même)
    whatsapp_url: str | None = None
    telegram_url: str | None = None
    outlook_compose_url: str | None = None


class ShareInfoOut(BaseModel):
    """Renvoyé par l'endpoint public (non authentifié) consulté par le destinataire."""
    is_valid: bool
    reason: str | None
    filenames: list[str]
    site_code: str | None
