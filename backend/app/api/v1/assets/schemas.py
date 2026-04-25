"""
AI-HRMS — Asset Management Pydantic v2 schemas.
"""

from __future__ import annotations

from datetime import date, datetime
from typing   import Optional
from uuid     import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Enums (string literals) ──────────────────────────────────────────────────

AssetCategory  = str   # laptop|desktop|mobile|tablet|monitor|keyboard|mouse|headset|sim_card|access_card|vehicle|furniture|other
AssetStatus    = str   # available|assigned|maintenance|retired|lost|disposed
AssetCondition = str   # excellent|good|fair|poor|damaged


# ─── Nested ───────────────────────────────────────────────────────────────────

class EmployeeMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            str
    employee_code: str
    full_name:     str
    department:    Optional[str] = None
    designation:   Optional[str] = None


# ─── Asset ────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    asset_tag:       Optional[str]  = Field(None, max_length=50)   # auto-generated if blank
    name:            str            = Field(..., min_length=2, max_length=200)
    category:        str            = "other"
    brand:           Optional[str]  = Field(None, max_length=100)
    model:           Optional[str]  = Field(None, max_length=200)
    serial_number:   Optional[str]  = Field(None, max_length=100)
    specifications:  Optional[dict] = None
    purchase_date:   Optional[date] = None
    purchase_cost:   Optional[int]  = Field(None, ge=0)
    current_value:   Optional[int]  = Field(None, ge=0)
    currency:        str            = "PKR"
    vendor:          Optional[str]  = Field(None, max_length=200)
    invoice_number:  Optional[str]  = Field(None, max_length=100)
    warranty_expiry: Optional[date] = None
    condition:       str            = "good"
    location:        Optional[str]  = Field(None, max_length=200)
    notes:           Optional[str]  = None
    is_mandatory_return: bool       = True   # must be returned on offboarding


class AssetUpdate(BaseModel):
    name:            Optional[str]  = None
    category:        Optional[str]  = None
    brand:           Optional[str]  = None
    model:           Optional[str]  = None
    serial_number:   Optional[str]  = None
    specifications:  Optional[dict] = None
    purchase_date:   Optional[date] = None
    purchase_cost:   Optional[int]  = None
    current_value:   Optional[int]  = None
    vendor:          Optional[str]  = None
    warranty_expiry: Optional[date] = None
    condition:       Optional[str]  = None
    status:          Optional[str]  = None
    location:        Optional[str]  = None
    notes:           Optional[str]  = None


class AssetAssignmentRequest(BaseModel):
    employee_id:             UUID
    condition_at_assignment: str            = "good"
    notes:                   Optional[str]  = None


class AssetReturnRequest(BaseModel):
    condition_at_return: str
    notes:               Optional[str] = None
    is_damaged:          bool          = False
    damage_description:  Optional[str] = None
    damage_cost:         Optional[int] = Field(None, ge=0)


class AssetFilterParams(BaseModel):
    category:    Optional[str]  = None
    status:      Optional[str]  = None
    assigned:    Optional[bool] = None   # True=assigned, False=unassigned
    search:      Optional[str]  = None
    page:        int            = Field(1, ge=1)
    page_size:   int            = Field(20, ge=1, le=100)


# ─── Response schemas ─────────────────────────────────────────────────────────

class AssetAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     str
    asset_id:               str
    employee_id:            str
    employee:               Optional[EmployeeMinimal] = None
    assigned_at:            date
    condition_at_assignment: str
    assignment_notes:       Optional[str]   = None
    returned_at:            Optional[date]  = None
    condition_at_return:    Optional[str]   = None
    return_notes:           Optional[str]   = None
    is_damaged:             bool
    damage_description:     Optional[str]   = None
    damage_cost:            Optional[int]   = None
    created_at:             datetime
    updated_at:             datetime


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              str
    asset_tag:       str
    name:            str
    category:        str
    brand:           Optional[str]  = None
    model:           Optional[str]  = None
    serial_number:   Optional[str]  = None
    specifications:  Optional[dict] = None
    purchase_date:   Optional[date] = None
    purchase_cost:   Optional[int]  = None
    current_value:   Optional[int]  = None
    currency:        str
    vendor:          Optional[str]  = None
    warranty_expiry: Optional[date] = None
    condition:       str
    status:          str
    location:        Optional[str]  = None
    notes:           Optional[str]  = None
    current_employee_id: Optional[str] = None
    current_employee:    Optional[EmployeeMinimal] = None
    assigned_since:  Optional[date] = None
    is_active:       bool
    created_at:      datetime
    updated_at:      datetime


class AssetListItem(BaseModel):
    """Compact schema for table rows."""
    model_config = ConfigDict(from_attributes=True)

    id:          str
    asset_tag:   str
    name:        str
    category:    str
    brand:       Optional[str] = None
    condition:   str
    status:      str
    current_employee: Optional[EmployeeMinimal] = None
    assigned_since:   Optional[date] = None
    warranty_expiry:  Optional[date] = None


class AssetListResponse(BaseModel):
    count:   int
    results: list[AssetListItem]
