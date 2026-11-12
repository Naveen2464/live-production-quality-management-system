from typing import List
from pydantic import BaseModel


class DropdownItem(BaseModel):
    id: int
    label: str
    code: str
    extra: dict = {}


class MasterDropdownsResponse(BaseModel):
    machines: List[DropdownItem]
    frames: List[DropdownItem]
    shifts: List[DropdownItem]
    customers: List[DropdownItem]
    operators: List[DropdownItem]
    supervisors: List[DropdownItem]

