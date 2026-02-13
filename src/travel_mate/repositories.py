from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional
from decimal import Decimal


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


from travel_mate.models import (
    AllowanceCalculation,
    ExpenseItem,
    Receipt,
    Reimbursement,
    Trip,
    UpdateSource,
)


class TripRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_customer(self, name: str, external_ref: str | None = None) -> int:
        cursor = self.conn.execute(
            "INSERT INTO customer(name, external_ref) VALUES (?, ?)",
            (name, external_ref),
        )
        return int(cursor.lastrowid)

    def create_project(self, customer_id: int, code: str, name: str, active: bool = True) -> int:
        cursor = self.conn.execute(
            "INSERT INTO project(customer_id, code, name, active) VALUES (?, ?, ?, ?)",
            (customer_id, code, name, int(active)),
        )
        return int(cursor.lastrowid)

    def create_trip(self, trip: Trip) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO trip(employee_name, project_id, customer_id, start_datetime, end_datetime, is_domestic, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trip.employee_name,
                trip.project_id,
                trip.customer_id,
                trip.start_datetime.isoformat(),
                trip.end_datetime.isoformat(),
                int(trip.is_domestic),
                trip.status,
            ),
        )
        return int(cursor.lastrowid)


class ExpenseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_expense_item(self, item: ExpenseItem) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO expense_item(
                trip_id, receipt_id, category, gross_amount, net_amount, vat_amount,
                currency, payment_method, receipt_link, booking_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.trip_id,
                item.receipt_id,
                item.category,
                _normalize_value(item.gross_amount),
                _normalize_value(item.net_amount),
                _normalize_value(item.vat_amount),
                item.currency,
                item.payment_method,
                item.receipt_link,
                item.booking_date.isoformat(),
            ),
        )
        return int(cursor.lastrowid)

    def create_allowance_calculation(self, calculation: AllowanceCalculation) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO allowance_calculation(
                trip_id, allowance_per_day, rule_version, meal_per_diem,
                deduction_amount, total_allowance, total_payable
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                calculation.trip_id,
                _normalize_value(calculation.allowance_per_day),
                calculation.rule_version,
                _normalize_value(calculation.meal_per_diem),
                _normalize_value(calculation.deduction_amount),
                _normalize_value(calculation.total_allowance),
                _normalize_value(calculation.total_payable),
            ),
        )
        return int(cursor.lastrowid)

    def create_reimbursement(self, reimbursement: Reimbursement) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO reimbursement(trip_id, expected_amount, paid_amount, paid_date, open_amount)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                reimbursement.trip_id,
                _normalize_value(reimbursement.expected_amount),
                _normalize_value(reimbursement.paid_amount),
                reimbursement.paid_date.isoformat() if reimbursement.paid_date else None,
                _normalize_value(reimbursement.open_amount),
            ),
        )
        return int(cursor.lastrowid)


class OwnershipRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_owner(self, entity_name: str, entity_id: int, field_name: str) -> Optional[str]:
        row = self.conn.execute(
            """
            SELECT owner_source
            FROM field_update_ownership
            WHERE entity_name = ? AND entity_id = ? AND field_name = ?
            """,
            (entity_name, entity_id, field_name),
        ).fetchone()
        return row[0] if row else None

    def set_owner(self, entity_name: str, entity_id: int, field_name: str, owner_source: UpdateSource) -> None:
        self.conn.execute(
            """
            INSERT INTO field_update_ownership(entity_name, entity_id, field_name, owner_source, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_name, entity_id, field_name)
            DO UPDATE SET owner_source = excluded.owner_source, updated_at = excluded.updated_at
            """,
            (entity_name, entity_id, field_name, owner_source, datetime.utcnow().isoformat()),
        )


class ReceiptRepository:
    UPDATABLE_FIELDS = {"ocr_text", "vendor", "receipt_date", "amount", "confidence", "processing_status"}

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, receipt: Receipt) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO receipt(file_path, ocr_text, vendor, receipt_date, amount, confidence, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.file_path,
                receipt.ocr_text,
                receipt.vendor,
                receipt.receipt_date.isoformat() if receipt.receipt_date else None,
                _normalize_value(receipt.amount),
                receipt.confidence,
                receipt.processing_status,
            ),
        )
        return int(cursor.lastrowid)

    def update_fields(self, receipt_id: int, fields: dict[str, Any]) -> None:
        if not fields:
            return
        invalid = set(fields) - self.UPDATABLE_FIELDS
        if invalid:
            raise ValueError(f"Invalid receipt fields: {sorted(invalid)}")

        assignments = ", ".join(f"{field} = ?" for field in fields)
        values = [_normalize_value(fields[field]) for field in fields]
        values.append(receipt_id)
        self.conn.execute(f"UPDATE receipt SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)

    def get_by_id(self, receipt_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM receipt WHERE id = ?", (receipt_id,)).fetchone()
