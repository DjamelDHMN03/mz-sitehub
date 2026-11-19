from pydantic import BaseModel


class MapLayerUpdate(BaseModel):
    name: str | None = None
    is_visible: bool | None = None
