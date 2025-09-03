# tests/test_safety_validators.py
import pytest
from safety_validators import InsulinSafetyValidator, validate_prescription_data
from exceptions import DoseTooHighError, ValidationError

class TestInsulinSafetyValidator:
    """Test insulin safety validation functionality"""

    def test_validate_single_dose_normal(self):
        """Test validation of normal safe doses"""
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 10, "breakfast")
        assert len(warnings) == 0

    def test_validate_single_dose_high_but_safe(self):
        """Test validation of high but still safe doses"""
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 25, "breakfast")
        assert len(warnings) == 0

    def test_validate_single_dose_exceeds_limit(self):
        """Test validation when dose exceeds safe limit"""
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 35, "breakfast")
        assert len(warnings) > 0
        assert "CRITICAL" in warnings[0]

    def test_validate_single_dose_extremely_high(self):
        """Test validation of extremely high dangerous doses"""
        with pytest.raises(DoseTooHighError):
            InsulinSafetyValidator.validate_single_dose("rapid", 50, "breakfast")

    def test_validate_single_dose_zero_dose(self):
        """Test validation of zero dose"""
        with pytest.raises(ValidationError):
            InsulinSafetyValidator.validate_single_dose("rapid", 0, "breakfast")

    def test_validate_single_dose_negative_dose(self):
        """Test validation of negative dose"""
        with pytest.raises(ValidationError):
            InsulinSafetyValidator.validate_single_dose("rapid", -5, "breakfast")

    def test_validate_single_dose_extremely_dangerous(self):
        """Test validation of life-threatening doses"""
        with pytest.raises(DoseTooHighError):
            InsulinSafetyValidator.validate_single_dose("rapid", 250, "breakfast")

    def test_validate_bedtime_dose_warning(self):
        """Test bedtime dose warning"""
        warnings = InsulinSafetyValidator.validate_single_dose("long", 30, "bedtime")
        assert len(warnings) > 0
        assert "BEDTIME DOSE" in warnings[0]

    def test_validate_daily_total_normal(self):
        """Test validation of normal daily total"""
        daily_doses = [
            {"actual_dose": 10, "insulin_type": "rapid"},
            {"actual_dose": 15, "insulin_type": "short"},
            {"actual_dose": 20, "insulin_type": "long"}
        ]
        warnings = InsulinSafetyValidator.validate_daily_total(daily_doses)
        assert len(warnings) == 0

    def test_validate_daily_total_exceeds_limit(self):
        """Test validation when daily total exceeds limit"""
        daily_doses = [
            {"actual_dose": 100, "insulin_type": "rapid"},
            {"actual_dose": 80, "insulin_type": "short"},
            {"actual_dose": 50, "insulin_type": "long"}
        ]
        warnings = InsulinSafetyValidator.validate_daily_total(daily_doses)
        assert len(warnings) > 0
        assert "CRITICAL" in warnings[0]

    def test_validate_daily_fast_acting_limit(self):
        """Test validation of fast-acting insulin daily limit"""
        daily_doses = [
            {"actual_dose": 60, "insulin_type": "rapid"},
            {"actual_dose": 50, "insulin_type": "short"},
            {"actual_dose": 20, "insulin_type": "long"}
        ]
        warnings = InsulinSafetyValidator.validate_daily_total(daily_doses)
        assert len(warnings) > 0
        assert "Fast-acting insulin" in warnings[0]

    def test_check_overdose_pattern_none(self):
        """Test overdose pattern detection with no overdoses"""
        daily_doses = [
            {"actual_dose": 10, "prescribed_dose": 10},
            {"actual_dose": 15, "prescribed_dose": 15}
        ]
        is_critical, warnings = InsulinSafetyValidator.check_overdose_pattern(daily_doses)
        assert not is_critical
        assert len(warnings) == 0

    def test_check_overdose_pattern_single_small(self):
        """Test overdose pattern with single small overdose"""
        daily_doses = [
            {"actual_dose": 12, "prescribed_dose": 10},
            {"actual_dose": 15, "prescribed_dose": 15}
        ]
        is_critical, warnings = InsulinSafetyValidator.check_overdose_pattern(daily_doses)
        assert not is_critical
        assert len(warnings) == 0

    def test_check_overdose_pattern_multiple_overdoses(self):
        """Test overdose pattern with multiple overdoses"""
        daily_doses = [
            {"actual_dose": 15, "prescribed_dose": 10},  # +5
            {"actual_dose": 20, "prescribed_dose": 15},  # +5
            {"actual_dose": 25, "prescribed_dose": 20}   # +5 = 15 total excess
        ]
        is_critical, warnings = InsulinSafetyValidator.check_overdose_pattern(daily_doses)
        assert is_critical
        assert len(warnings) > 0
        assert "CRITICAL OVERDOSE PATTERN" in warnings[0]

    def test_check_overdose_pattern_high_excess(self):
        """Test overdose pattern with high total excess"""
        daily_doses = [
            {"actual_dose": 25, "prescribed_dose": 10},  # +15 units (exceeds threshold)
        ]
        is_critical, warnings = InsulinSafetyValidator.check_overdose_pattern(daily_doses)
        assert is_critical
        assert len(warnings) > 0
        assert "CRITICAL OVERDOSE PATTERN" in warnings[0]


class TestPrescriptionDataValidation:
    """Test prescription data validation"""

    def test_validate_prescription_data_valid(self):
        """Test validation of valid prescription data"""
        valid_data = {
            "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid"},
            "lunch": {"insulin": "Novolin R", "dose": 15, "type": "short"},
            "dinner": {"insulin": "Lantus", "dose": 20, "type": "long"}
        }
        # Should not raise any exception
        validate_prescription_data(valid_data)

    def test_validate_prescription_data_empty(self):
        """Test validation of empty prescription data"""
        with pytest.raises(ValidationError):
            validate_prescription_data({})

    def test_validate_prescription_data_none(self):
        """Test validation of None prescription data"""
        with pytest.raises(ValidationError):
            validate_prescription_data(None)

    def test_validate_prescription_data_invalid_structure(self):
        """Test validation of invalid prescription structure"""
        with pytest.raises(ValidationError):
            validate_prescription_data("invalid_string")

    def test_validate_prescription_data_missing_insulin(self):
        """Test validation with missing insulin field"""
        invalid_data = {
            "breakfast": {"dose": 10, "type": "rapid"}  # Missing insulin
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "Missing required field 'insulin'" in str(exc_info.value)

    def test_validate_prescription_data_missing_dose(self):
        """Test validation with missing dose field"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "type": "rapid"}  # Missing dose
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "Missing required field 'dose'" in str(exc_info.value)

    def test_validate_prescription_data_missing_type(self):
        """Test validation with missing type field"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "dose": 10}  # Missing type
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "Missing required field 'type'" in str(exc_info.value)

    def test_validate_prescription_data_invalid_dose_zero(self):
        """Test validation with zero dose"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "dose": 0, "type": "rapid"}
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "must be greater than 0" in str(exc_info.value)

    def test_validate_prescription_data_invalid_dose_negative(self):
        """Test validation with negative dose"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "dose": -5, "type": "rapid"}
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "must be greater than 0" in str(exc_info.value)

    def test_validate_prescription_data_invalid_dose_string(self):
        """Test validation with string dose"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "dose": "ten", "type": "rapid"}
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "must be a number" in str(exc_info.value)

    def test_validate_prescription_data_invalid_type(self):
        """Test validation with invalid insulin type"""
        invalid_data = {
            "breakfast": {"insulin": "Humalog", "dose": 10, "type": "invalid_type"}
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "Invalid insulin type" in str(exc_info.value)

    def test_validate_prescription_data_invalid_meal_structure(self):
        """Test validation with invalid meal structure"""
        invalid_data = {
            "breakfast": "invalid_structure"  # Should be dict
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(invalid_data)
        assert "must be a dictionary" in str(exc_info.value)

    def test_validate_prescription_data_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid entries"""
        mixed_data = {
            "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid"},  # Valid
            "lunch": {"insulin": "Novolin", "dose": "invalid", "type": "short"}  # Invalid dose
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_prescription_data(mixed_data)
        assert "must be a number" in str(exc_info.value)


class TestInsulinTypeSpecificValidation:
    """Test insulin type specific validation rules"""

    def test_rapid_insulin_limits(self):
        """Test rapid insulin specific limits"""
        # Normal dose
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 20, "breakfast")
        assert len(warnings) == 0

        # High but acceptable
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 30, "breakfast")
        assert len(warnings) == 0

        # Exceeds limit
        warnings = InsulinSafetyValidator.validate_single_dose("rapid", 35, "breakfast")
        assert len(warnings) > 0

    def test_long_insulin_limits(self):
        """Test long-acting insulin specific limits"""
        # Normal dose
        warnings = InsulinSafetyValidator.validate_single_dose("long", 40, "bedtime")
        assert len(warnings) == 0

        # High but acceptable
        warnings = InsulinSafetyValidator.validate_single_dose("long", 80, "bedtime")
        assert len(warnings) > 0  # Should warn for bedtime

        # Exceeds limit
        warnings = InsulinSafetyValidator.validate_single_dose("long", 90, "breakfast")
        assert len(warnings) > 0

    def test_intermediate_insulin_limits(self):
        """Test intermediate insulin specific limits"""
        warnings = InsulinSafetyValidator.validate_single_dose("intermediate", 50, "breakfast")
        assert len(warnings) == 0

        warnings = InsulinSafetyValidator.validate_single_dose("intermediate", 70, "breakfast")
        assert len(warnings) > 0

    def test_mixed_insulin_limits(self):
        """Test mixed insulin specific limits"""
        warnings = InsulinSafetyValidator.validate_single_dose("mixed", 40, "breakfast")
        assert len(warnings) == 0

        warnings = InsulinSafetyValidator.validate_single_dose("mixed", 60, "breakfast")
        assert len(warnings) > 0
