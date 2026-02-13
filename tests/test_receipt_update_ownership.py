from decimal import Decimal

from travel_mate.db import apply_sqlite_migration, connect_sqlite
from travel_mate.models import Receipt
from travel_mate.repositories import OwnershipRepository, ReceiptRepository
from travel_mate.services import ReceiptUpdateService


def test_manual_correction_wins_over_ocr_updates():
    conn = connect_sqlite()
    apply_sqlite_migration(conn, "migrations/sqlite/001_initial_schema.sql")

    receipt_repo = ReceiptRepository(conn)
    ownership_repo = OwnershipRepository(conn)
    service = ReceiptUpdateService(conn)

    receipt_id = receipt_repo.create(
        Receipt(file_path="/tmp/receipt-1.png", processing_status="pending", amount=Decimal("19.99"))
    )

    ocr_result = service.apply_ocr_update(receipt_id, {"vendor": "Auto OCR Vendor", "amount": Decimal("20.10")})
    manual_result = service.apply_manual_correction(receipt_id, {"vendor": "Manual Vendor"})
    second_ocr_result = service.apply_ocr_update(receipt_id, {"vendor": "Override OCR Vendor", "ocr_text": "raw text"})

    persisted = receipt_repo.get_by_id(receipt_id)

    assert ocr_result == {"updated": ["amount", "vendor"], "skipped": []}
    assert manual_result == {"updated": ["vendor"], "skipped": []}
    assert second_ocr_result == {"updated": ["ocr_text"], "skipped": ["vendor"]}
    assert persisted["vendor"] == "Manual Vendor"
    assert persisted["ocr_text"] == "raw text"
    assert ownership_repo.get_owner("receipt", receipt_id, "vendor") == "manual"
    assert ownership_repo.get_owner("receipt", receipt_id, "ocr_text") == "ocr"
