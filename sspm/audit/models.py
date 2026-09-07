from pydantic import BaseModel


class InventoryTool(BaseModel):
    name: str
    package: str
    version: str
    license: str
    role: str
    on_path: bool = False
