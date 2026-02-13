from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

UpdateSource = Literal["ocr", "manual", "system"]


@dataclass(frozen=True)
class Trip:
    employee_name: str
    project_id: int
    customer_id: int
    start_datetime: datetime
    end_datetime: datetime
    is_domestic: bool
    status: str


@dataclass(frozen=True)
class ExpenseItem:
    trip_id: int
    category: str
    gross_amount: Decimal
    net_amount: Optional[Decimal]
    vat_amount: Optional[Decimal]
    currency: str
    payment_method: str
    receipt_link: Optional[str]
    booking_date: date
    receipt_id: Optional[int] = None


@dataclass(frozen=True)
class Receipt:
    file_path: str
    processing_status: str
    ocr_text: Optional[str] = None
    vendor: Optional[str] = None
    receipt_date: Optional[date] = None
    amount: Optional[Decimal] = None
    confidence: Optional[float] = None


@dataclass(frozen=True)
class AllowanceCalculation:
    trip_id: int
    allowance_per_day: Decimal
    rule_version: str
    meal_per_diem: Decimal
    deduction_amount: Decimal
    total_allowance: Decimal
    total_payable: Decimal


@dataclass(frozen=True)
class Reimbursement:
    trip_id: int
    expected_amount: Decimal
    paid_amount: Decimal
    open_amount: Decimal
    paid_date: Optional[date] = None
