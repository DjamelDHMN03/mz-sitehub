from pydantic import BaseModel


class SyncPreviewItemOut(BaseModel):
    row_number: int
    code: str | None
    action: str  # CREATE, UPDATE, INCHANGE, IGNORE_NO_CODE
    changes: dict[str, list] = {}  # {champ: [ancienne, nouvelle]} — sérialisable JSON
    warnings: list[str] = []


class ExcelPreviewResult(BaseModel):
    import_id: str  # référence temporaire pour la confirmation (section 60)
    detected_columns: dict[str, int]
    unmatched_headers: list[str]
    items: list[SyncPreviewItemOut]
    summary: dict[str, int]  # {"CREATE": n, "UPDATE": n, "INCHANGE": n, "IGNORE_NO_CODE": n}


class ExcelConfirmRequest(BaseModel):
    import_id: str
    apply_creates: bool = True
    apply_updates: bool = True
