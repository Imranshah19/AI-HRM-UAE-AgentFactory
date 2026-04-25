"""
AI-HRMS — Designation Pydantic v2 schemas.
"""

import uuid
from pydantic import BaseModel, ConfigDict, Field


class DesignationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name:          str             = Field(..., min_length=1, max_length=200)
    department_id: uuid.UUID | None = None
    level:         str | None      = Field(None, max_length=50)
    grade:         str | None      = Field(None, max_length=20)
    min_salary:    int | None      = Field(None, ge=0)
    max_salary:    int | None      = Field(None, ge=0)


class DesignationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name:          str | None      = Field(None, max_length=200)
    department_id: uuid.UUID | None = None
    level:         str | None      = Field(None, max_length=50)
    grade:         str | None      = Field(None, max_length=20)
    min_salary:    int | None      = Field(None, ge=0)
    max_salary:    int | None      = Field(None, ge=0)
    is_active:     bool | None     = None


class DesignationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    name:          str
    department_id: uuid.UUID | None
    level:         str | None
    grade:         str | None
    min_salary:    int | None
    max_salary:    int | None
    is_active:     bool
