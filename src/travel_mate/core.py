from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


ISO_TS = "%Y-%m-%dT%H:%M:%S.%fZ"


@dataclass(frozen=True)
class ChangeLogEntry:
    entity_type: str
    entity_id: str
    field_name: str
    old_value: Any
    new_value: Any
    changed_at: str = field(default_factory=lambda: utc_now())


@dataclass
class ExpenseItem:
    expense_id: str
    merchant: str | None = None
    amount: Decimal | None = None
    spent_on: date | None = None
    category: str | None = None
    receipt_path: str | None = None
    image_hash: str | None = None
    change_log: list[ChangeLogEntry] = field(default_factory=list)

    def update(self, **changes: Any) -> list[ChangeLogEntry]:
        entries: list[ChangeLogEntry] = []
        for field_name, new_value in changes.items():
            if not hasattr(self, field_name):
                raise AttributeError(f"Unknown field: {field_name}")
            old_value = getattr(self, field_name)
            if old_value != new_value:
                setattr(self, field_name, new_value)
                entry = ChangeLogEntry(
                    entity_type="expense",
                    entity_id=self.expense_id,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                )
                self.change_log.append(entry)
                entries.append(entry)
        return entries

    def fingerprint(self) -> str | None:
        if self.amount is None or self.spent_on is None or not self.merchant:
            return None
        normalized = normalize_merchant(self.merchant)
        raw = f"{self.amount}:{self.spent_on.isoformat()}:{normalized}".encode("utf-8")
        return sha256(raw).hexdigest()


@dataclass
class ValidationResult:
    ready_for_export: bool
    blockers: list[str]


@dataclass(frozen=True)
class ExportSnapshot:
    snapshot_id: str
    trip_id: str
    generated_at: str
    payload: dict[str, Any]


@dataclass
class Trip:
    trip_id: str
    name: str
    expenses: list[ExpenseItem] = field(default_factory=list)
    change_log: list[ChangeLogEntry] = field(default_factory=list)

    def add_expense(self, expense: ExpenseItem) -> None:
        self.expenses.append(expense)
        self.change_log.append(
            ChangeLogEntry(
                entity_type="trip",
                entity_id=self.trip_id,
                field_name="expenses",
                old_value=None,
                new_value=expense.expense_id,
            )
        )

    def validate(self) -> ValidationResult:
        blockers: list[str] = []
        for expense in self.expenses:
            missing: list[str] = []
            for required in ["merchant", "amount", "spent_on", "category", "receipt_path"]:
                if getattr(expense, required) in (None, ""):
                    missing.append(required)
            if missing:
                blockers.append(
                    f"Expense {expense.expense_id} missing mandatory fields: {', '.join(missing)}"
                )
        duplicate_warnings = self.find_duplicate_receipts()
        blockers.extend(duplicate_warnings)
        return ValidationResult(ready_for_export=not blockers, blockers=blockers)

    def find_duplicate_receipts(self) -> list[str]:
        by_fingerprint: dict[str, str] = {}
        by_image_hash: dict[str, str] = {}
        duplicates: list[str] = []
        for expense in self.expenses:
            fp = expense.fingerprint()
            if fp:
                seen = by_fingerprint.get(fp)
                if seen:
                    duplicates.append(
                        f"Duplicate receipt fingerprint between expenses {seen} and {expense.expense_id}"
                    )
                else:
                    by_fingerprint[fp] = expense.expense_id
            if expense.image_hash:
                seen_hash = by_image_hash.get(expense.image_hash)
                if seen_hash:
                    duplicates.append(
                        f"Duplicate receipt image hash between expenses {seen_hash} and {expense.expense_id}"
                    )
                else:
                    by_image_hash[expense.image_hash] = expense.expense_id
        return duplicates

    def create_export_payload(self) -> dict[str, Any]:
        validation = self.validate()
        if not validation.ready_for_export:
            raise ValueError(
                "Trip is not ready_for_export. Resolve blockers first: "
                + "; ".join(validation.blockers)
            )
        return {
            "trip_id": self.trip_id,
            "trip_name": self.name,
            "generated_at": utc_now(),
            "expenses": [
                {
                    "expense_id": e.expense_id,
                    "merchant": e.merchant,
                    "amount": str(e.amount),
                    "spent_on": e.spent_on.isoformat() if e.spent_on else None,
                    "category": e.category,
                    "receipt_path": e.receipt_path,
                    "image_hash": e.image_hash,
                }
                for e in self.expenses
            ],
        }


@dataclass
class ExportSnapshotStore:
    base_dir: Path

    def save_snapshot(self, trip: Trip) -> ExportSnapshot:
        payload = trip.create_export_payload()
        timestamp = utc_now()
        snapshot = ExportSnapshot(
            snapshot_id=str(uuid4()),
            trip_id=trip.trip_id,
            generated_at=timestamp,
            payload=payload,
        )

        trip_dir = self.base_dir / "exports" / trip.trip_id
        trip_dir.mkdir(parents=True, exist_ok=True)
        file_path = trip_dir / f"{timestamp}.json"
        # Immutable write: fail if the exact snapshot file already exists.
        with file_path.open("x", encoding="utf-8") as f:
            json.dump(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "trip_id": snapshot.trip_id,
                    "generated_at": snapshot.generated_at,
                    "payload": snapshot.payload,
                },
                f,
                indent=2,
            )
        return snapshot


@dataclass
class SecureStorage:
    base_dir: Path

    def upload_path(self, trip_id: str, filename: str) -> Path:
        trip_id_safe = sanitize_identifier(trip_id)
        filename_safe = sanitize_filename(filename)
        trip_dir = self.base_dir / "uploads" / trip_id_safe
        trip_dir.mkdir(parents=True, exist_ok=True)
        path = trip_dir / filename_safe
        resolved = path.resolve()
        if not str(resolved).startswith(str(trip_dir.resolve())):
            raise ValueError("Unsafe upload path")
        return resolved


@dataclass
class RetentionSettings:
    snapshot_retention_days: int = 365
    upload_retention_days: int = 365

    def prune(self, base_dir: Path, now: datetime | None = None) -> list[Path]:
        now = now or datetime.now(timezone.utc)
        deleted: list[Path] = []
        deleted.extend(
            prune_older_than(base_dir / "exports", now - timedelta(days=self.snapshot_retention_days))
        )
        deleted.extend(
            prune_older_than(base_dir / "uploads", now - timedelta(days=self.upload_retention_days))
        )
        return deleted


def prune_older_than(root: Path, cutoff: datetime) -> list[Path]:
    if not root.exists():
        return []
    deleted: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file():
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                path.unlink()
                deleted.append(path)
    return deleted


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(ISO_TS)


def normalize_merchant(merchant: str) -> str:
    return re.sub(r"\s+", " ", merchant.strip().lower())


def sanitize_identifier(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value)
    return safe.strip("_") or "trip"


def sanitize_filename(value: str) -> str:
    value = Path(value).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value)
    return safe or "upload.bin"
