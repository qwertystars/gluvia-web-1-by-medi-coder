# prescription_service.py
import json
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from database import Prescription, DoseLog, User as DBUser
from models import DoseTableResponse, QuestionnaireResponse, DailyScheduleResponse

def get_current_meal() -> str:
    """Determine current meal based on system time using enhanced logic"""
    now = datetime.now()
    current_hour = now.hour

    if 6 <= current_hour < 10:
        return "breakfast"
    elif 10 <= current_hour < 12:
        return "mid_morning"
    elif 12 <= current_hour < 18:
        return "lunch"
    elif 18 <= current_hour < 22:
        return "dinner"
    else:
        return "snack"

def calculate_scheduled_time(meal_time: str, base_date: datetime = None) -> datetime:
    """Calculate scheduled time for a given meal with enhanced meal types"""
    if base_date is None:
        base_date = datetime.now()

    meal_times = {
        "breakfast": time(8, 0),     # 8:00 AM
        "mid_morning": time(10, 30), # 10:30 AM
        "lunch": time(13, 0),        # 1:00 PM
        "dinner": time(19, 0),       # 7:00 PM
        "bedtime": time(22, 0),      # 10:00 PM
        "snack": time(16, 0)         # 4:00 PM (default snack time)
    }

    scheduled_time = meal_times.get(meal_time, time(12, 0))
    return datetime.combine(base_date.date(), scheduled_time)

def calculate_dose_with_onset(insulin_type: str, full_dose: float, gap_minutes: int, onset_minutes: int = None) -> Tuple[float, str]:
    """
    Enhanced dose calculation considering insulin onset times
    gap_minutes: minutes since scheduled dose
    onset_minutes: onset time in minutes for the insulin
    Returns: adjusted dose and advice string
    """

    # Default onset times by insulin type (in minutes)
    default_onsets = {
        "rapid": 15,
        "short": 30,
        "intermediate": 90,
        "long": 60,
        "mixed": 30
    }

    onset = onset_minutes or default_onsets.get(insulin_type, 30)

    # If within onset time, take full dose
    if gap_minutes <= onset:
        return full_dose, f"✅ Take full dose now ({full_dose} units) - within onset period"

    # Beyond onset, calculate based on insulin type
    if insulin_type == "rapid":
        if gap_minutes <= 60:
            partial = round(full_dose * 0.6, 1)
            return partial, f"⚠️ Take partial dose ({partial} units) - after onset but manageable"
        else:
            return 0, "❌ Too late for rapid dose; monitor blood sugar closely"

    elif insulin_type == "short":
        if gap_minutes <= 120:
            partial = round(full_dose * 0.5, 1)
            return partial, f"⚠️ Take partial dose ({partial} units) - after onset"
        else:
            return 0, "❌ Too late for short-acting insulin; monitor blood sugar"

    elif insulin_type == "intermediate":
        if gap_minutes <= 240:
            partial = round(full_dose * 0.75, 1)
            return partial, f"⚠️ Take partial dose ({partial} units) - can still be effective"
        else:
            return 0, "❌ Missed dose; monitor blood sugar closely"

    elif insulin_type == "long":
        if gap_minutes <= 480:
            partial = round(full_dose * 0.5, 1)
            return partial, f"⚠️ Take partial dose ({partial} units) - long-acting can compensate"
        else:
            return full_dose, "⏰ Take next scheduled dose as planned - continue routine"

    elif insulin_type == "mixed":
        if gap_minutes <= 180:
            partial = round(full_dose * 0.7, 1)
            return partial, f"⚠️ Take partial dose ({partial} units) - mixed insulin adjustment"
        else:
            return 0, "❌ Too late for mixed dose; monitor blood sugar"

    else:
        return 0, "❌ Unknown insulin type - consult healthcare provider"

def verify_dose_taken_enhanced(prescribed_dose: float, actual_dose: float) -> str:
    """Enhanced verification of actual dose taken"""
    difference = abs(actual_dose - prescribed_dose)
    percentage_diff = (difference / prescribed_dose) * 100 if prescribed_dose > 0 else 0

    if actual_dose == prescribed_dose:
        return "✅ Correct dose taken"
    elif actual_dose > prescribed_dose:
        if percentage_diff <= 10:
            return f"✅ Close to prescribed dose (+{difference:.1f} units) - acceptable range"
        else:
            return f"⚠️ Took {difference:.1f} units MORE than prescribed. Monitor for low blood sugar signs"
    else:
        if percentage_diff <= 10:
            return f"✅ Close to prescribed dose (-{difference:.1f} units) - acceptable range"
        else:
            return f"⚠️ Took {difference:.1f} units LESS than prescribed. Monitor blood sugar closely"

def process_questionnaire_data(db: Session, user_id: int, questionnaire_data: List[Dict]) -> DailyScheduleResponse:
    """Process questionnaire responses and generate daily schedule with advice"""

    prescription = get_active_prescription(db, user_id)
    if not prescription:
        raise ValueError("No active prescription found")

    prescription_data = json.loads(prescription.prescription_data)
    now = datetime.now()
    current_meal = get_current_meal()

    # Define meal order for processing
    meal_order = ["breakfast", "mid_morning", "lunch", "dinner", "snack"]
    schedule = []

    # Convert questionnaire data to dict for easier lookup
    questionnaire_dict = {item['meal_time']: item for item in questionnaire_data}

    for meal in meal_order:
        if meal in prescription_data:
            dose_info = prescription_data[meal]
            insulin = dose_info.get("insulin", "Unknown")
            prescribed_dose = dose_info.get("dose", 0)
            insulin_type = dose_info.get("type", "rapid")
            onset = dose_info.get("onset", 30)  # Default onset 30 minutes

            response_data = questionnaire_dict.get(meal)

            if response_data:
                if response_data['taken']:
                    # Dose was taken
                    actual_dose = response_data.get('actual_dose', prescribed_dose)
                    advice = verify_dose_taken_enhanced(prescribed_dose, actual_dose)
                    status = f"Taken: {actual_dose} units"

                    # Log the dose
                    log_dose(
                        db=db,
                        user_id=user_id,
                        prescription_id=prescription.id,
                        meal_time=meal,
                        insulin_name=insulin,
                        insulin_type=insulin_type,
                        prescribed_dose=prescribed_dose,
                        status="taken",
                        actual_dose=actual_dose
                    )

                else:
                    # Dose was missed - calculate what to do
                    if response_data.get('meal_scheduled_time'):
                        # Parse the meal time they provided
                        meal_time_str = response_data['meal_scheduled_time']
                        meal_time = datetime.strptime(meal_time_str, "%H:%M")
                        meal_time = meal_time.replace(year=now.year, month=now.month, day=now.day)
                        gap_minutes = (now - meal_time).total_seconds() / 60
                        if gap_minutes < 0:
                            gap_minutes += 24 * 60  # Handle next day scenario
                    else:
                        # Use scheduled meal time
                        scheduled_time = calculate_scheduled_time(meal)
                        gap_minutes = (now - scheduled_time).total_seconds() / 60

                    adjusted_dose, advice = calculate_dose_with_onset(
                        insulin_type, prescribed_dose, int(gap_minutes), onset
                    )
                    status = f"Missed → {adjusted_dose} units recommended"

                    # Log as missed
                    log_dose(
                        db=db,
                        user_id=user_id,
                        prescription_id=prescription.id,
                        meal_time=meal,
                        insulin_name=insulin,
                        insulin_type=insulin_type,
                        prescribed_dose=prescribed_dose,
                        status="missed",
                        actual_dose=None
                    )
            else:
                # No response provided - check if it's a future meal or current
                meal_index = meal_order.index(meal)
                current_index = meal_order.index(current_meal) if current_meal in meal_order else len(meal_order)

                if meal_index <= current_index:
                    status = f"{prescribed_dose} units (Status unknown)"
                    advice = "Please update your dose status"
                else:
                    status = f"{prescribed_dose} units (Take as scheduled)"
                    advice = "Take as usual when time comes"

            schedule.append(QuestionnaireResponse(
                meal=meal.title(),
                insulin=insulin,
                prescribed_dose=prescribed_dose,
                status=status,
                advice=advice,
                adjusted_dose=response_data.get('actual_dose') if response_data and response_data['taken'] else None
            ))

    return DailyScheduleResponse(
        current_time=now.strftime('%H:%M'),
        current_zone=current_meal.upper(),
        schedule=schedule
    )

def get_active_prescription(db: Session, user_id: int) -> Optional[Prescription]:
    """Get the active prescription for a user"""
    return db.query(Prescription).filter(
        Prescription.user_id == user_id,
        Prescription.is_active == True
    ).first()

def log_dose(db: Session, user_id: int, prescription_id: int, meal_time: str,
             insulin_name: str, insulin_type: str, prescribed_dose: float,
             status: str, actual_dose: float = None, actual_time: datetime = None) -> DoseLog:
    """Log a dose entry"""

    # Check for existing dose log for the same meal on the same day
    today = datetime.now().date()
    existing_dose = db.query(DoseLog).filter(
        DoseLog.user_id == user_id,
        DoseLog.meal_time == meal_time,
        DoseLog.created_at >= datetime.combine(today, datetime.min.time()),
        DoseLog.created_at < datetime.combine(today, datetime.max.time())
    ).first()

    if existing_dose:
        # Update the existing dose instead of creating a new one
        scheduled_time = calculate_scheduled_time(meal_time)
        now = datetime.now()

        # Ensure actual_time is timezone-naive if provided
        if actual_time and actual_time.tzinfo is not None:
            actual_time = actual_time.replace(tzinfo=None)

        # Calculate gap in minutes
        if actual_time:
            gap_minutes = int((actual_time - scheduled_time).total_seconds() / 60)
        else:
            gap_minutes = int((now - scheduled_time).total_seconds() / 60)

        # Calculate adjusted dose and advice
        if status == "missed":
            adjusted_dose, advice = calculate_dose_adjustment(insulin_type, gap_minutes, prescribed_dose)
        elif status == "taken" and actual_dose:
            adjusted_dose = actual_dose
            advice = verify_dose_taken(prescribed_dose, actual_dose)
        else:
            adjusted_dose = prescribed_dose
            advice = "✅ Taken as prescribed"

        # Update existing dose log
        existing_dose.status = status
        existing_dose.actual_dose = actual_dose
        existing_dose.actual_time = (actual_time or now).replace(tzinfo=timezone.utc)
        existing_dose.gap_minutes = max(0, gap_minutes)
        existing_dose.adjusted_dose = adjusted_dose
        existing_dose.advice = advice

        db.commit()
        db.refresh(existing_dose)
        return existing_dose

    # No existing dose found, create a new one
    scheduled_time = calculate_scheduled_time(meal_time)
    now = datetime.now()  # Keep timezone-naive for consistency

    # Ensure actual_time is timezone-naive if provided
    if actual_time and actual_time.tzinfo is not None:
        actual_time = actual_time.replace(tzinfo=None)

    # Calculate gap in minutes
    if actual_time:
        gap_minutes = int((actual_time - scheduled_time).total_seconds() / 60)
    else:
        gap_minutes = int((now - scheduled_time).total_seconds() / 60)

    # Calculate adjusted dose and advice
    if status == "missed":
        adjusted_dose, advice = calculate_dose_adjustment(insulin_type, gap_minutes, prescribed_dose)
    elif status == "taken" and actual_dose:
        adjusted_dose = actual_dose
        advice = verify_dose_taken(prescribed_dose, actual_dose)
    else:
        adjusted_dose = prescribed_dose
        advice = "✅ Taken as prescribed"

    # Convert to UTC for database storage
    scheduled_time_utc = scheduled_time.replace(tzinfo=timezone.utc)
    actual_time_utc = (actual_time or now).replace(tzinfo=timezone.utc)

    dose_log = DoseLog(
        user_id=user_id,
        prescription_id=prescription_id,
        meal_time=meal_time,
        insulin_name=insulin_name,
        insulin_type=insulin_type,
        prescribed_dose=prescribed_dose,
        actual_dose=actual_dose,
        scheduled_time=scheduled_time_utc,
        actual_time=actual_time_utc,
        status=status,
        gap_minutes=max(0, gap_minutes),  # Don't allow negative gaps
        adjusted_dose=adjusted_dose,
        advice=advice
    )

    db.add(dose_log)
    db.commit()
    db.refresh(dose_log)
    return dose_log

def get_current_meal_doses(db: Session, user_id: int) -> List[DoseTableResponse]:
    """Get available doses for current meal time"""
    current_meal = get_current_meal()
    prescription = get_active_prescription(db, user_id)

    if not prescription:
        return []

    prescription_data = json.loads(prescription.prescription_data)
    doses = []

    # Get doses for current and past meals only
    meal_order = ["breakfast", "lunch", "snack", "dinner", "bedtime"]
    current_index = meal_order.index(current_meal) if current_meal in meal_order else len(meal_order)

    for i, meal in enumerate(meal_order):
        if i <= current_index and meal in prescription_data:
            dose_info = prescription_data[meal]

            # Check if this dose was already logged today
            today = datetime.now().date()
            # Create timezone-aware datetime for today's start
            today_start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)

            existing_log = db.query(DoseLog).filter(
                DoseLog.user_id == user_id,
                DoseLog.meal_time == meal,
                DoseLog.created_at >= today_start,
                DoseLog.created_at <= today_end,
                DoseLog.status == "taken"  # Only count actually taken doses
            ).first()

            if existing_log:
                # Dose was taken today
                status_advice = f"✅ {existing_log.advice or 'Dose completed'}"
                doses.append(DoseTableResponse(
                    meal=meal.title(),
                    insulin=dose_info.get("insulin", "Unknown"),
                    prescribed_dose=dose_info.get("dose", 0),
                    status_advice=status_advice,
                    actual_dose=existing_log.actual_dose,
                    gap_minutes=existing_log.gap_minutes
                ))
            else:
                # Check if dose was missed (logged as missed today)
                missed_log = db.query(DoseLog).filter(
                    DoseLog.user_id == user_id,
                    DoseLog.meal_time == meal,
                    DoseLog.created_at >= today_start,
                    DoseLog.created_at <= today_end,
                    DoseLog.status == "missed"
                ).first()

                if missed_log:
                    # Dose was marked as missed today
                    status_advice = f"❌ {missed_log.advice or 'Dose missed'}"
                    doses.append(DoseTableResponse(
                        meal=meal.title(),
                        insulin=dose_info.get("insulin", "Unknown"),
                        prescribed_dose=dose_info.get("dose", 0),
                        status_advice=status_advice,
                        gap_minutes=missed_log.gap_minutes
                    ))
                else:
                    # Dose not logged yet - calculate if overdue
                    scheduled_time = calculate_scheduled_time(meal)
                    now = datetime.now()
                    gap_minutes = int((now - scheduled_time).total_seconds() / 60)

                    if gap_minutes > 30:  # More than 30 minutes late
                        adjusted_dose, advice = calculate_dose_adjustment(
                            dose_info.get("type", "rapid"),
                            gap_minutes,
                            dose_info.get("dose", 0)
                        )
                        status_advice = f"⏰ {advice}"
                    else:
                        status_advice = "⏳ Pending"

                    doses.append(DoseTableResponse(
                        meal=meal.title(),
                        insulin=dose_info.get("insulin", "Unknown"),
                        prescribed_dose=dose_info.get("dose", 0),
                        status_advice=status_advice,
                        gap_minutes=max(0, gap_minutes) if gap_minutes > 0 else None
                    ))

    return doses

def get_dose_history(db: Session, user_id: int, days: int = 7) -> List[DoseLog]:
    """Get dose history for specified number of days"""
    start_date = datetime.now() - timedelta(days=days)
    start_date_utc = start_date.replace(tzinfo=timezone.utc)
    return db.query(DoseLog).filter(
        DoseLog.user_id == user_id,
        DoseLog.created_at >= start_date_utc
    ).order_by(DoseLog.created_at.desc()).all()

def calculate_dose_adjustment(insulin_type: str, gap_minutes: int, prescribed_dose: float) -> Tuple[float, str]:
    """Legacy function that calls the enhanced version for backward compatibility"""
    return calculate_dose_with_onset(insulin_type, prescribed_dose, gap_minutes)

def verify_dose_taken(prescribed_dose: float, actual_dose: float) -> str:
    """Legacy function that calls the enhanced version for backward compatibility"""
    return verify_dose_taken_enhanced(prescribed_dose, actual_dose)

def create_prescription(
    db: Session,
    user_id: int,
    prescription_data: Dict[str, Any],
    doctor_name: Optional[str] = None,
    doctor_phone: Optional[str] = None,
    doctor_email: Optional[str] = None,
    clinic_name: Optional[str] = None,
    prescription_date: Optional[datetime] = None
) -> Prescription:
    """Create a new prescription with proper validation"""

    # Validate prescription data structure
    if not prescription_data or not isinstance(prescription_data, dict):
        raise ValueError("Invalid prescription data: must be a non-empty dictionary")

    # Validate that at least one meal has proper insulin data
    valid_meals = []
    for meal, insulin_info in prescription_data.items():
        if isinstance(insulin_info, dict) and all(key in insulin_info for key in ['insulin', 'dose', 'type']):
            valid_meals.append(meal)

    if not valid_meals:
        raise ValueError("Invalid prescription data: no valid meal entries found")

    # Deactivate any existing prescriptions for this user
    db.query(Prescription).filter(
        Prescription.user_id == user_id,
        Prescription.is_active == True
    ).update({"is_active": False})

    # Create new prescription
    db_prescription = Prescription(
        user_id=user_id,
        doctor_name=doctor_name,
        doctor_phone=doctor_phone,
        doctor_email=doctor_email,
        clinic_name=clinic_name,
        prescription_date=prescription_date or datetime.now(timezone.utc),
        prescription_data=json.dumps(prescription_data),
        is_active=True
    )

    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription
