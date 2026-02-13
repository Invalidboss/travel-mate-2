# travel-mate-2

Travel expense domain logic that now supports:

- Change logs for trip and expense updates (field-level old/new + timestamp).
- Duplicate receipt detection using amount/date/merchant fingerprint and image hash.
- Validation workflow with `ready_for_export` and actionable blockers.
- Immutable export snapshots by `trip_id` and generation timestamp.
- Secure upload paths under `uploads/{trip_id}/...` with sanitization.
- Retention settings for pruning old uploads/snapshots.
- Validation summary rendering for UI before final Excel export.

## Quick example

```python
from datetime import date
from decimal import Decimal
from pathlib import Path

from travel_mate.core import ExpenseItem, ExportSnapshotStore, Trip
from travel_mate.ui import render_validation_summary

trip = Trip(trip_id="trip-123", name="London")
trip.add_expense(
    ExpenseItem(
        expense_id="exp-1",
        merchant="Metro",
        amount=Decimal("14.50"),
        spent_on=date(2026, 2, 1),
        category="Transport",
        receipt_path="uploads/trip-123/metro.png",
    )
)

validation = trip.validate()
print(validation.ready_for_export)
print(render_validation_summary(validation))

store = ExportSnapshotStore(base_dir=Path("."))
snapshot = store.save_snapshot(trip)
print(snapshot)
```

## Run tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
