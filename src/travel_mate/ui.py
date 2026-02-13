from __future__ import annotations

from html import escape

from .core import ValidationResult


def render_validation_summary(validation: ValidationResult) -> str:
    if validation.ready_for_export:
        return (
            '<section class="validation-summary success">'
            "<h2>Validation Summary</h2>"
            "<p>Ready for export ✅</p>"
            "</section>"
        )

    items = "".join(f"<li>{escape(blocker)}</li>" for blocker in validation.blockers)
    return (
        '<section class="validation-summary error">'
        "<h2>Validation Summary</h2>"
        "<p>Resolve the blockers below before generating the final Excel export.</p>"
        f"<ul>{items}</ul>"
        "</section>"
    )
