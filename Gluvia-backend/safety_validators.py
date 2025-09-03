# safety_validators.py
"""
Critical safety validators for insulin dose management
"""
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import logging
from exceptions import DoseTooHighError, ValidationError

logger = logging.getLogger(__name__)

class InsulinSafetyValidator:
    """Validates insulin doses for safety concerns"""

    # Maximum safe doses per insulin type (units)
    MAX_SINGLE_DOSES = {
        "rapid": 30,
        "short": 40,
        "intermediate": 60,
        "long": 80,
        "mixed": 50
    }

    # Maximum daily totals
    MAX_DAILY_TOTAL = 200  # Total units per day
    MAX_BOLUS_DAILY = 100  # Fast-acting insulin per day
    CRITICAL_EXCESS_THRESHOLD = 10  # Units above prescribed considered critical

    @classmethod
    def validate_single_dose(cls, insulin_type: str, dose: float, meal_time: str) -> List[str]:
        """Validate a single dose for safety"""
        warnings = []

        if dose <= 0:
            raise ValidationError("Dose must be greater than 0")

        if dose > 200:
            raise DoseTooHighError(f"Dose {dose} units is extremely dangerous - seek immediate medical help")

        max_dose = cls.MAX_SINGLE_DOSES.get(insulin_type, 30)

        if dose > max_dose:
            warnings.append(f"⚠️ CRITICAL: {dose} units exceeds safe limit for {insulin_type} insulin ({max_dose} units)")

        if dose > max_dose * 1.5:
            raise DoseTooHighError(f"Dose {dose} units is dangerously high - contact doctor immediately")

        # Bedtime dose warnings
        if meal_time == "bedtime" and dose > 25:
            warnings.append("⚠️ HIGH BEDTIME DOSE: Risk of nighttime hypoglycemia")

        return warnings

    @classmethod
    def validate_daily_total(cls, daily_doses: List[Dict[str, Any]]) -> List[str]:
        """Validate total daily insulin intake"""
        warnings = []

        total_units = sum(dose.get('actual_dose', 0) for dose in daily_doses if dose.get('actual_dose'))
        fast_acting_units = sum(
            dose.get('actual_dose', 0) for dose in daily_doses
            if dose.get('actual_dose') and dose.get('insulin_type') in ['rapid', 'short']
        )

        if total_units > cls.MAX_DAILY_TOTAL:
            warnings.append(f"🚨 CRITICAL: Daily total {total_units} units exceeds safe limit ({cls.MAX_DAILY_TOTAL} units)")

        if fast_acting_units > cls.MAX_BOLUS_DAILY:
            warnings.append(f"🚨 WARNING: Fast-acting insulin total {fast_acting_units} units exceeds recommended daily limit")

        return warnings

    @classmethod
    def check_overdose_pattern(cls, daily_doses: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Check for dangerous overdose patterns"""
        warnings = []
        overdose_count = 0
        total_excess = 0

        for dose in daily_doses:
            actual = dose.get('actual_dose', 0)
            prescribed = dose.get('prescribed_dose', 0)

            if actual > prescribed:
                excess = actual - prescribed
                total_excess += excess
                overdose_count += 1

        is_critical = overdose_count >= 2 or total_excess > cls.CRITICAL_EXCESS_THRESHOLD

        if is_critical:
            warnings.append(f"🚨🚨 CRITICAL OVERDOSE PATTERN: {overdose_count} overdoses, {total_excess} excess units")
            warnings.append("🚨🚨 SEEK IMMEDIATE MEDICAL ATTENTION")

        return is_critical, warnings

def validate_prescription_data(prescription_data: Dict[str, Any]) -> None:
    """Validate prescription data structure"""
    if not prescription_data or not isinstance(prescription_data, dict):
        raise ValidationError("Invalid prescription data: must be a non-empty dictionary")

    required_fields = ['insulin', 'dose', 'type']

    for meal, insulin_info in prescription_data.items():
        if not isinstance(insulin_info, dict):
            raise ValidationError(f"Invalid insulin info for {meal}: must be a dictionary")

        for field in required_fields:
            if field not in insulin_info:
                raise ValidationError(f"Missing required field '{field}' for {meal}")

        # Validate dose is a number
        try:
            dose = float(insulin_info['dose'])
            if dose <= 0:
                raise ValidationError(f"Invalid dose for {meal}: must be greater than 0")
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid dose for {meal}: must be a number")

        # Validate insulin type
        valid_types = ['rapid', 'short', 'intermediate', 'long', 'mixed']
        if insulin_info['type'] not in valid_types:
            raise ValidationError(f"Invalid insulin type for {meal}: must be one of {valid_types}")
