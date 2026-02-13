from __future__ import annotations

import sqlite3
from typing import Any

from travel_mate.models import ExpenseItem, Receipt, Trip
from travel_mate.repositories import ExpenseRepository, OwnershipRepository, ReceiptRepository, TripRepository


class TravelSetupService:
    """Application service for setting up report dimensions and trip records."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.trips = TripRepository(conn)

    def create_trip_with_dimensions(self, trip: Trip, project_code: str, project_name: str, customer_name: str) -> int:
        with self.conn:
            customer_id = self.trips.create_customer(customer_name)
            project_id = self.trips.create_project(customer_id, project_code, project_name)
            enriched_trip = Trip(
                employee_name=trip.employee_name,
                project_id=project_id,
                customer_id=customer_id,
                start_datetime=trip.start_datetime,
                end_datetime=trip.end_datetime,
                is_domestic=trip.is_domestic,
                status=trip.status,
            )
            return self.trips.create_trip(enriched_trip)


class ExpenseService:
    def __init__(self, conn: sqlite3.Connection):
        self.expenses = ExpenseRepository(conn)
        self.receipts = ReceiptRepository(conn)
        self.conn = conn

    def attach_receipt_to_expense(self, receipt: Receipt, expense_item: ExpenseItem) -> tuple[int, int]:
        with self.conn:
            receipt_id = self.receipts.create(receipt)
            expense_id = self.expenses.create_expense_item(
                ExpenseItem(
                    trip_id=expense_item.trip_id,
                    receipt_id=receipt_id,
                    category=expense_item.category,
                    gross_amount=expense_item.gross_amount,
                    net_amount=expense_item.net_amount,
                    vat_amount=expense_item.vat_amount,
                    currency=expense_item.currency,
                    payment_method=expense_item.payment_method,
                    receipt_link=expense_item.receipt_link,
                    booking_date=expense_item.booking_date,
                )
            )
            return receipt_id, expense_id


class ReceiptUpdateService:
    """Coordinates ownership-aware receipt updates from OCR and human corrections."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.receipts = ReceiptRepository(conn)
        self.ownership = OwnershipRepository(conn)

    def apply_ocr_update(self, receipt_id: int, fields: dict[str, Any], force: bool = False) -> dict[str, list[str]]:
        applied: dict[str, Any] = {}
        skipped: list[str] = []

        for field, value in fields.items():
            owner = self.ownership.get_owner("receipt", receipt_id, field)
            if owner == "manual" and not force:
                skipped.append(field)
                continue
            applied[field] = value

        with self.conn:
            self.receipts.update_fields(receipt_id, applied)
            for field in applied:
                self.ownership.set_owner("receipt", receipt_id, field, "ocr")

        return {"updated": sorted(applied.keys()), "skipped": sorted(skipped)}

    def apply_manual_correction(self, receipt_id: int, fields: dict[str, Any]) -> dict[str, list[str]]:
        with self.conn:
            self.receipts.update_fields(receipt_id, fields)
            for field in fields:
                self.ownership.set_owner("receipt", receipt_id, field, "manual")

        return {"updated": sorted(fields.keys()), "skipped": []}
