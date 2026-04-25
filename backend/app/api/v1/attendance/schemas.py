"""
AI-HRMS — Attendance & Time Tracking Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, time
from typing   import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class AttendanceStatus(str, enum.Enum):
    present  = "present"
    late     = "late"
    absent   = "absent"
    half_day = "half_day"
    on_leave = "on_leave"
    holiday  = "holiday"
    weekend  = "weekend"


class CheckInSource(str, enum.Enum):
    manual    = "manual"
    mobile    = "mobile"
    biometric = "biometric"
    geo       = "geo"


class AdjustmentStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


# ─── Shift ────────────────────────────────────────────────────────────────────

class ShiftCreate(BaseModel):
    name:                 str  = Field(..., min_length=2, max_length=100)
    start_time:           time  # e.g. "09:00:00"
    end_time:             time
    grace_period_minutes: int  = Field(15, ge=0, le=120)
    is_active:            bool = True

    @model_validator(mode="after")
    def end_after_start(self) -> "ShiftCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    @property
    def total_hours(self) -> float:
        from datetime import datetime as _dt
        s = _dt.combine(_dt.today(), self.start_time)
        e = _dt.combine(_dt.today(), self.end_time)
        return (e - s).total_seconds() / 3600


class ShiftUpdate(BaseModel):
    name:                 Optional[str]  = Field(None, min_length=2, max_length=100)
    start_time:           Optional[time] = None
    end_time:             Optional[time] = None
    grace_period_minutes: Optional[int]  = Field(None, ge=0, le=120)
    is_active:            Optional[bool] = None


class ShiftResponse(BaseModel):
    id:                   str
    name:                 str
    start_time:           time
    end_time:             time
    grace_period_minutes: int
    total_hours:          float
    is_active:            bool

    model_config = {"from_attributes": True}


# ─── Location ─────────────────────────────────────────────────────────────────

class LocationData(BaseModel):
    lat:     float = Field(..., ge=-90,  le=90)
    lng:     float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)


# ─── Check-in / Check-out ─────────────────────────────────────────────────────

class AttendanceCheckInRequest(BaseModel):
    source:   CheckInSource  = CheckInSource.manual
    location: Optional[LocationData] = None
    notes:    Optional[str]  = Field(None, max_length=500)

    @model_validator(mode="after")
    def location_required_for_geo(self) -> "AttendanceCheckInRequest":
        if self.source == CheckInSource.geo and not self.location:
            raise ValueError("location is required when source=geo")
        return self


class AttendanceCheckOutRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)


# ─── Manual entry ─────────────────────────────────────────────────────────────

class AttendanceManualEntryRequest(BaseModel):
    employee_id: str
    date:        date
    check_in:    datetime
    check_out:   Optional[datetime] = None
    reason:      str = Field(..., min_length=10, max_length=500)
    source:      CheckInSource = CheckInSource.manual

    @model_validator(mode="after")
    def checkout_after_checkin(self) -> "AttendanceManualEntryRequest":
        if self.check_out and self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


# ─── Adjustment ───────────────────────────────────────────────────────────────

class AttendanceAdjustmentRequest(BaseModel):
    attendance_id:   str
    new_check_in:    datetime
    new_check_out:   Optional[datetime] = None
    reason:          str = Field(..., min_length=10, max_length=500)

    @model_validator(mode="after")
    def checkout_after_checkin(self) -> "AttendanceAdjustmentRequest":
        if self.new_check_out and self.new_check_out <= self.new_check_in:
            raise ValueError("new_check_out must be after new_check_in")
        return self


class AdjustmentReviewRequest(BaseModel):
    action:      str  = Field(..., pattern="^(approve|reject)$")
    review_note: Optional[str] = Field(None, max_length=500)


# ─── Employee minimal ─────────────────────────────────────────────────────────

class EmployeeMinimal(BaseModel):
    id:                str
    full_name:         str
    employee_code:     str
    photo_url:         Optional[str] = None
    department_name:   Optional[str] = None
    designation_title: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Attendance Record ────────────────────────────────────────────────────────

class AttendanceRecordResponse(BaseModel):
    id:               str
    employee_id:      str
    employee:         EmployeeMinimal
    date:             date
    check_in:         Optional[datetime]
    check_out:        Optional[datetime]
    working_hours:    Optional[float]    # decimal hours
    overtime_hours:   Optional[float]
    status:           AttendanceStatus
    source:           CheckInSource
    location_lat:     Optional[float]
    location_lng:     Optional[float]
    location_address: Optional[str]
    notes:            Optional[str]
    is_manual:        bool
    shift_id:         Optional[str]
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


class AttendanceRecordListItem(BaseModel):
    id:             str
    employee_id:    str
    employee_name:  str
    employee_code:  str
    department_name: Optional[str]
    date:           date
    check_in:       Optional[datetime]
    check_out:      Optional[datetime]
    working_hours:  Optional[float]
    overtime_hours: Optional[float]
    status:         AttendanceStatus
    source:         CheckInSource
    is_manual:      bool

    model_config = {"from_attributes": True}


class AttendanceRecordListResponse(BaseModel):
    count:   int
    results: list[AttendanceRecordListItem]


# ─── Adjustment Record ────────────────────────────────────────────────────────

class AdjustmentResponse(BaseModel):
    id:               str
    attendance_id:    str
    employee_id:      str
    employee_name:    str
    original_check_in:  Optional[datetime]
    original_check_out: Optional[datetime]
    requested_check_in:  datetime
    requested_check_out: Optional[datetime]
    reason:           str
    status:           AdjustmentStatus
    reviewed_by:      Optional[str]
    review_note:      Optional[str]
    reviewed_at:      Optional[datetime]
    created_at:       datetime

    model_config = {"from_attributes": True}


# ─── Summary ──────────────────────────────────────────────────────────────────

class AttendanceSummary(BaseModel):
    employee_id:           str
    employee_name:         str
    month:                 int
    year:                  int
    total_working_days:    int   # weekdays excluding holidays
    present_days:          int
    absent_days:           int
    late_days:             int
    half_days:             int
    leave_days:            int
    holiday_days:          int
    total_working_hours:   float
    total_overtime_hours:  float
    attendance_percentage: float  # present/total_working_days * 100


# ─── Timesheet ────────────────────────────────────────────────────────────────

class TimesheetRow(BaseModel):
    date:           date
    day_name:       str                # "Monday"
    check_in:       Optional[datetime]
    check_out:      Optional[datetime]
    working_hours:  Optional[float]
    overtime_hours: Optional[float]
    status:         AttendanceStatus
    is_weekend:     bool
    is_holiday:     bool
    holiday_name:   Optional[str]
    notes:          Optional[str]
    attendance_id:  Optional[str]      # for adjustment reference


class TimesheetResponse(BaseModel):
    employee_id:   str
    employee_name: str
    month:         int
    year:          int
    rows:          list[TimesheetRow]
    total_working_hours:  float
    total_overtime_hours: float
    total_present_days:   int


# ─── Live / WebSocket ─────────────────────────────────────────────────────────

class LiveAttendanceEntry(BaseModel):
    employee_id:     str
    employee_name:   str
    photo_url:       Optional[str]
    department_name: Optional[str]
    action:          str   # "check_in" | "check_out"
    time:            datetime
    check_in_time:   Optional[datetime]  # used for live status display
    status:          AttendanceStatus

    model_config = {"from_attributes": True}


# ─── Filters ──────────────────────────────────────────────────────────────────

class AttendanceFilterParams(BaseModel):
    employee_id:   Optional[str]              = None
    department_id: Optional[str]              = None
    date:          Optional[date]             = None
    date_from:     Optional[date]             = None
    date_to:       Optional[date]             = None
    status:        Optional[AttendanceStatus] = None
    source:        Optional[CheckInSource]    = None
    page:          int = Field(1,  ge=1)
    page_size:     int = Field(25, ge=1, le=100)
