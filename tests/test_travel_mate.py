from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from travel_mate.core import ExpenseItem, ExportSnapshotStore, RetentionSettings, SecureStorage, Trip
from travel_mate.ui import render_validation_summary


class TravelMateTestCase(unittest.TestCase):
    def test_change_log_and_validation(self):
        trip = Trip(trip_id="trip-1", name="Berlin")
        expense = ExpenseItem(expense_id="exp-1")
        trip.add_expense(expense)

        changes = expense.update(
            merchant="Coffee Shop",
            amount=Decimal("12.30"),
            spent_on=date(2026, 1, 3),
            category="Meals",
            receipt_path="uploads/trip-1/receipt.png",
            image_hash="hash-1",
        )

        self.assertTrue(changes)
        self.assertEqual(changes[0].entity_type, "expense")
        self.assertTrue(trip.validate().ready_for_export)

    def test_duplicate_detection_blocks_export(self):
        trip = Trip(trip_id="trip-2", name="Paris")
        e1 = ExpenseItem(
            expense_id="exp-1",
            merchant="Cafe Nero",
            amount=Decimal("9.50"),
            spent_on=date(2026, 2, 10),
            category="Meals",
            receipt_path="uploads/trip-2/r1.png",
            image_hash="same-image",
        )
        e2 = ExpenseItem(
            expense_id="exp-2",
            merchant="cafe nero",
            amount=Decimal("9.50"),
            spent_on=date(2026, 2, 10),
            category="Meals",
            receipt_path="uploads/trip-2/r2.png",
            image_hash="same-image",
        )
        trip.add_expense(e1)
        trip.add_expense(e2)

        validation = trip.validate()
        self.assertFalse(validation.ready_for_export)
        self.assertGreaterEqual(len(validation.blockers), 2)
        html = render_validation_summary(validation)
        self.assertIn("Validation Summary", html)
        self.assertIn("Resolve the blockers", html)

    def test_immutable_snapshot_and_secure_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            trip = Trip(trip_id="trip-3", name="Rome")
            trip.add_expense(
                ExpenseItem(
                    expense_id="exp-1",
                    merchant="Taxi",
                    amount=Decimal("20.00"),
                    spent_on=date(2026, 3, 15),
                    category="Transport",
                    receipt_path="uploads/trip-3/r1.png",
                )
            )

            store = ExportSnapshotStore(base_dir=base)
            snapshot = store.save_snapshot(trip)
            self.assertEqual(snapshot.trip_id, "trip-3")

            storage = SecureStorage(base_dir=base)
            upload = storage.upload_path("trip-3", "../../unsafe.png")
            self.assertTrue(str(upload).endswith("uploads/trip-3/unsafe.png"))

    def test_retention_prunes_old_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            old_file = base / "uploads" / "trip-1" / "old.txt"
            old_file.parent.mkdir(parents=True, exist_ok=True)
            old_file.write_text("old")

            very_old = datetime.now(timezone.utc) - timedelta(days=20)
            ts = very_old.timestamp()
            old_file.touch()
            import os

            os.utime(old_file, (ts, ts))

            settings = RetentionSettings(snapshot_retention_days=10, upload_retention_days=10)
            deleted = settings.prune(base)
            self.assertIn(old_file, deleted)
            self.assertFalse(old_file.exists())


if __name__ == "__main__":
    unittest.main()
