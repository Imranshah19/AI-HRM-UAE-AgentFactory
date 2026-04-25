"""
AI-HRMS — Department Pydantic v2 schemas.
"""

import uuid
from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name:        str            = Field(..., min_length=1, max_length=200)
    code:        str | None     = Field(None, max_length=20)
    description: str | None     = Field(None, max_length=500)
    parent_id:   uuid.UUID | None = None


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name:        str | None     = Field(None, min_length=1, max_length=200)
    code:        str | None     = Field(None, max_length=20)
    description: str | None     = Field(None, max_length=500)
    parent_id:   uuid.UUID | None = None
    is_active:   bool | None    = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          uuid.UUID
    name:        str
    code:        str | None
    description: str | None
    parent_id:   uuid.UUID | None
    is_active:   bool
    employee_count: int = 0
