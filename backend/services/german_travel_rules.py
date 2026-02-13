from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Sequence, Tuple


RULE_VERSION = "DE_TRAVEL_RULES_2026_01"

DOMESTIC_FULL_DAY_RATE = Decimal("28.00")
DOMESTIC_PARTIAL_DAY_RATE = Decimal("14.00")

MEAL_DEDUCTION_RATES = {
    "breakfast": Decimal("0.20"),
    "lunch": Decimal("0.40"),
    "dinner": Decimal("0.40"),
}

# Example international country/day rates.
# Extend/replace using published legal rates as required.
INTERNATIONAL_RATE_TABLE: Dict[str, Dict[str, Decimal]] = {
    "AT": {"full_day": Decimal("40.00"), "partial_day": Decimal("27.00")},
    "CH": {"full_day": Decimal("64.00"), "partial_day": Decimal("43.00")},
    "FR": {"full_day": Decimal("53.00"), "partial_day": Decimal("35.00")},
    "NL": {"full_day": Decimal("47.00"), "partial_day": Decimal("32.00")},
}


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    amount: Decimal


@dataclass(frozen=True)
class DayMealProvision:
    day: date
    breakfast: bool = False
    lunch: bool = False
    dinner: bool = False


@dataclass(frozen=True)
class TripSegment:
    trip_id: str
    start: datetime
    end: datetime
    country_code: str = "DE"
    city: Optional[str] = None
    provided_meals: Sequence[DayMealProvision] = field(default_factory=tuple)
    receipts: Sequence[Receipt] = field(default_factory=tuple)


class TravelRuleValidationError(ValueError):
    """Raised when travel data violates rule preconditions."""


class GermanTravelRulesService:
    """Calculation service with versioned logic and traceable steps."""

    rule_version = RULE_VERSION

    def calculate_and_persist(self, segments: Sequence[TripSegment]) -> Dict[str, object]:
        """
        Calculate reimbursable per-diems and return payload suitable for persistence.

        The returned payload includes `rule_version` to keep historic legal context.
        """
        calculation = self.calculate(segments)
        return {
            "rule_version": self.rule_version,
            "totals": calculation["totals"],
            "calculation_steps": calculation["calculation_steps"],
            "by_trip": calculation["by_trip"],
        }

    def calculate(self, segments: Sequence[TripSegment]) -> Dict[str, object]:
        self._validate_segments(segments)

        steps: List[str] = [f"Applying rule version: {self.rule_version}"]
        by_trip: List[Dict[str, object]] = []

        gross_total = Decimal("0.00")
        meal_deduction_total = Decimal("0.00")

        for segment in sorted(segments, key=lambda s: s.start):
            segment_steps: List[str] = []
            rates = self._get_rates_for_country(segment.country_code)
            is_domestic = segment.country_code.upper() == "DE"

            segment_steps.append(
                f"Trip {segment.trip_id}: {'domestic' if is_domestic else 'international'} rates "
                f"(full_day={rates['full_day']}, partial_day={rates['partial_day']})."
            )

            day_allowance, day_steps = self._calculate_day_allowance(segment, rates)
            segment_steps.extend(day_steps)

            meal_deduction, meal_steps = self._calculate_meal_deductions(segment, rates["full_day"])
            segment_steps.extend(meal_steps)

            reimbursable = _money(day_allowance - meal_deduction)
            gross_total += day_allowance
            meal_deduction_total += meal_deduction

            segment_steps.append(
                f"Trip {segment.trip_id} subtotal = {day_allowance} - {meal_deduction} = {reimbursable}."
            )

            steps.extend(segment_steps)
            by_trip.append(
                {
                    "trip_id": segment.trip_id,
                    "country_code": segment.country_code.upper(),
                    "gross_allowance": str(_money(day_allowance)),
                    "meal_deductions": str(_money(meal_deduction)),
                    "net_allowance": str(reimbursable),
                    "calculation_steps": segment_steps,
                }
            )

        net_total = _money(gross_total - meal_deduction_total)
        totals = {
            "gross_allowance": str(_money(gross_total)),
            "meal_deductions": str(_money(meal_deduction_total)),
            "net_allowance": str(net_total),
        }

        steps.append(
            f"Overall total = gross {totals['gross_allowance']} - deductions {totals['meal_deductions']} = {totals['net_allowance']}."
        )

        return {
            "rule_version": self.rule_version,
            "totals": totals,
            "calculation_steps": steps,
            "by_trip": by_trip,
        }

    def _validate_segments(self, segments: Sequence[TripSegment]) -> None:
        if not segments:
            raise TravelRuleValidationError("At least one trip segment is required.")

        for segment in segments:
            if segment.start is None or segment.end is None:
                raise TravelRuleValidationError(
                    f"Trip {segment.trip_id} has missing start/end datetime."
                )
            if segment.end <= segment.start:
                raise TravelRuleValidationError(
                    f"Trip {segment.trip_id} has impossible time span (end before/equal start)."
                )

        self._validate_overlaps(segments)
        self._validate_duplicate_receipts(segments)

    def _validate_overlaps(self, segments: Sequence[TripSegment]) -> None:
        ordered = sorted(segments, key=lambda s: s.start)
        for prev, current in zip(ordered, ordered[1:]):
            if current.start < prev.end:
                raise TravelRuleValidationError(
                    f"Trips {prev.trip_id} and {current.trip_id} overlap."
                )

    def _validate_duplicate_receipts(self, segments: Sequence[TripSegment]) -> None:
        seen: Dict[str, str] = {}
        for segment in segments:
            for receipt in segment.receipts:
                owner = seen.get(receipt.receipt_id)
                if owner is not None:
                    raise TravelRuleValidationError(
                        f"Duplicate receipt id {receipt.receipt_id} in trips {owner} and {segment.trip_id}."
                    )
                seen[receipt.receipt_id] = segment.trip_id

    def _calculate_day_allowance(
        self,
        segment: TripSegment,
        rates: Dict[str, Decimal],
    ) -> Tuple[Decimal, List[str]]:
        steps: List[str] = []

        start_day = segment.start.date()
        end_day = segment.end.date()

        if start_day == end_day:
            duration = segment.end - segment.start
            minimum_hours = Decimal("8")
            worked_hours = Decimal(duration.total_seconds()) / Decimal("3600")
            if worked_hours >= minimum_hours:
                amount = rates["partial_day"]
                steps.append(
                    f"Single-day trip {start_day}: absence {worked_hours:.2f}h >= 8h, partial-day rate {amount}."
                )
            else:
                amount = Decimal("0.00")
                steps.append(
                    f"Single-day trip {start_day}: absence {worked_hours:.2f}h < 8h, no per diem."
                )
            return _money(amount), steps

        total = Decimal("0.00")
        current = start_day
        while current <= end_day:
            if current == start_day or current == end_day:
                total += rates["partial_day"]
                steps.append(
                    f"{current}: arrival/departure partial-day rate {rates['partial_day']}."
                )
            else:
                total += rates["full_day"]
                steps.append(f"{current}: full-day rate {rates['full_day']}.")
            current += timedelta(days=1)

        return _money(total), steps

    def _calculate_meal_deductions(
        self,
        segment: TripSegment,
        full_day_rate: Decimal,
    ) -> Tuple[Decimal, List[str]]:
        provided_by_day = {entry.day: entry for entry in segment.provided_meals}

        total = Decimal("0.00")
        steps: List[str] = []
        current_day = segment.start.date()
        while current_day <= segment.end.date():
            meals = provided_by_day.get(current_day)
            if meals is None:
                current_day += timedelta(days=1)
                continue

            day_total = Decimal("0.00")
            for meal_key, ratio in MEAL_DEDUCTION_RATES.items():
                provided = getattr(meals, meal_key)
                if provided:
                    deduction = _money(full_day_rate * ratio)
                    day_total += deduction
                    steps.append(
                        f"{current_day}: {meal_key} provided, deduct {ratio * 100:.0f}% of full-day rate = {deduction}."
                    )

            if day_total:
                total += day_total
                steps.append(f"{current_day}: meal deduction subtotal {day_total}.")
            current_day += timedelta(days=1)

        if total == 0:
            steps.append(f"Trip {segment.trip_id}: no meal deductions.")

        return _money(total), steps

    def _get_rates_for_country(self, country_code: str) -> Dict[str, Decimal]:
        normalized = country_code.upper()
        if normalized == "DE":
            return {
                "full_day": DOMESTIC_FULL_DAY_RATE,
                "partial_day": DOMESTIC_PARTIAL_DAY_RATE,
            }
        if normalized not in INTERNATIONAL_RATE_TABLE:
            raise TravelRuleValidationError(
                f"No international per-diem rates configured for country code {normalized}."
            )
        return INTERNATIONAL_RATE_TABLE[normalized]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


__all__ = [
    "RULE_VERSION",
    "Receipt",
    "DayMealProvision",
    "TripSegment",
    "TravelRuleValidationError",
    "GermanTravelRulesService",
]
