# routes/consolidated_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import json
import logging

from auth import get_current_user
from database import get_db, User as DBUser
from models import PrescriptionCreate, PrescriptionResponse
from prescription_service import (
    create_prescription, get_active_prescription, log_dose,
    get_dose_history
)
from safety_validators import InsulinSafetyValidator, validate_prescription_data
from exceptions import DoseTooHighError, ValidationError, validation_exception, internal_server_exception
from ocr import run_ocr, process_pdf_to_base64, process_image_to_base64

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

# Prescription chart with all insulin types (matching your provided logic)
PRESCRIPTION_TEMPLATE = {
    "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid", "onset": 15},
    "mid_morning": {"insulin": "Regular", "dose": 8, "type": "short", "onset": 30},
    "lunch": {"insulin": "Novolin N", "dose": 15, "type": "intermediate", "onset": 90},
    "dinner": {"insulin": "Lantus", "dose": 20, "type": "long", "onset": 60},
    "snack": {"insulin": "Mix 70/30", "dose": 12, "type": "mixed", "onset": 30},
}

def calculate_adjusted_dose(insulin_type: str, full_dose: float, gap: float, onset: int) -> tuple[float, str]:
    """
    Calculate adjusted dose based on gap and onset time
    gap: minutes since scheduled dose
    onset: onset time in minutes
    Returns: (adjusted_dose, advice_string)
    """
    # If within onset time, take full dose
    if gap <= onset:
        return full_dose, "Take full dose now (within onset period)."

    # Beyond onset, use logic for partial/too late
    if insulin_type == "rapid":
        if gap <= 60:
            partial = round(full_dose * 0.6, 1)
            return partial, f"Take partial dose ({partial} units) now (after onset)."
        else:
            return 0, "Too late for rapid dose; monitor blood sugar."

    elif insulin_type == "short":
        if gap <= 120:
            partial = round(full_dose * 0.5, 1)
            return partial, f"Take partial dose ({partial} units) now (after onset)."
        else:
            return 0, "Too late for short-acting insulin; monitor blood sugar."

    elif insulin_type == "intermediate":
        if gap <= 240:
            partial = round(full_dose * 0.75, 1)
            return partial, f"Take partial dose ({partial} units) now (after onset)."
        else:
            return 0, "Missed dose; monitor blood sugar closely."

    elif insulin_type == "long":
        if gap <= 480:
            partial = round(full_dose * 0.5, 1)
            return partial, f"Take partial dose ({partial} units) now (after onset)."
        else:
            return full_dose, "Too late for previous dose; continue next scheduled dose."

    elif insulin_type == "mixed":
        if gap <= 180:
            partial = round(full_dose * 0.7, 1)
            return partial, f"Take partial dose ({partial} units) now (after onset)."
        else:
            return 0, "Too late for mixed dose; monitor blood sugar."

    else:
        return 0, "Unknown insulin type."

def detect_current_meal_zone() -> str:
    """Detect current meal zone based on time"""
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

# CONSOLIDATED ENDPOINTS

@router.post("/upload")
async def upload_prescription(
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload endpoint:
    - Accepts PDF or image files
    - Converts pages/images to base64 strings
    - Sends them to OpenAI for OCR/extraction
    - Automatically creates a prescription from the extracted data
    """
    try:
        images_base64 = []

        # Handle PDFs
        if file.content_type == "application/pdf":
            contents = await file.read()
            images_base64 = process_pdf_to_base64(contents, max_pages=3)

        # Handle images
        elif file.content_type in ["image/jpeg", "image/png", "image/jpg"]:
            contents = await file.read()
            encoded = process_image_to_base64(contents)
            images_base64 = [encoded]

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be PDF or image (JPEG, PNG, JPG)"
            )

        if not images_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process file - no images extracted"
            )

        # Run OCR to extract prescription data and doctor info
        try:
            prescription_data, doctor_info = run_ocr(images_base64)

            # Validate extracted prescription data
            if not prescription_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No insulin prescriptions found in the uploaded file"
                )

            # Validate prescription data format
            validate_prescription_data(prescription_data)

            # Create prescription in database
            db_prescription = create_prescription(
                db=db,
                user_id=current_user.id,
                prescription_data=prescription_data,  # Pass as dict, not JSON string
                doctor_name=doctor_info.get("doctor_name"),
                doctor_phone=doctor_info.get("doctor_phone"),
                doctor_email=doctor_info.get("doctor_email"),
                clinic_name=doctor_info.get("clinic_name"),
                prescription_date=doctor_info.get("date")
            )

            logger.info(f"Prescription uploaded and created for user {current_user.id}")

            return {
                "message": "Prescription uploaded and processed successfully",
                "prescription_id": db_prescription.id,
                "extracted_data": prescription_data,
                "doctor_info": doctor_info,
                "prescription": {
                    "id": db_prescription.id,
                    "doctor_name": db_prescription.doctor_name,
                    "clinic_name": db_prescription.clinic_name,
                    "created_at": db_prescription.created_at.isoformat() if db_prescription.created_at else None,
                    "is_active": db_prescription.is_active
                }
            }

        except json.JSONDecodeError as e:
            logger.error(f"OCR JSON parsing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse OCR results - please try with a clearer image"
            )
        except ValidationError as e:
            raise validation_exception(str(e))
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )

@router.post("/", response_model=PrescriptionResponse)
def create_or_update_prescription(
    prescription: PrescriptionCreate,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new prescription for the current user"""
    try:
        db_prescription = create_prescription(
            db=db,
            user_id=current_user.id,
            prescription_data=prescription.prescription_data,
            doctor_name=prescription.doctor_name,
            doctor_phone=prescription.doctor_phone,
            doctor_email=prescription.doctor_email,
            clinic_name=prescription.clinic_name,
            prescription_date=prescription.prescription_date
        )
        return db_prescription
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create prescription: {str(e)}"
        )

@router.get("/active", response_model=PrescriptionResponse)
def get_active_prescription_info(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the active prescription for the current user"""
    prescription = get_active_prescription(db, current_user.id)
    if not prescription:
        raise HTTPException(
            status_code=404,
            detail="No active prescription found"
        )
    return prescription

@router.get("/status")
def get_comprehensive_status(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive status including current meal zone, prescription info, and today's doses"""
    # Get current meal zone
    current_meal = detect_current_meal_zone()
    now = datetime.now()

    # Get active prescription
    prescription = get_active_prescription(db, current_user.id)
    if not prescription:
        raise HTTPException(
            status_code=404,
            detail="No active prescription found"
        )

    prescription_data = json.loads(prescription.prescription_data)

    # Get today's dose history
    dose_history = get_dose_history(db, current_user.id, 1)

    return {
        "current_time": now.strftime('%H:%M'),
        "current_zone": current_meal.upper(),
        "prescription_data": prescription_data,
        "today_doses": dose_history,
        "meal_options": ["breakfast", "mid_morning", "lunch", "dinner", "snack"]
    }

@router.post("/daily-questionnaire", response_model=Dict[str, Any])
def process_comprehensive_questionnaire(
    questionnaire_data: Dict[str, Any],
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process daily questionnaire with comprehensive insulin management logic
    Handles multiple inputs with warnings and provides detailed advice
    """
    try:
        # Get active prescription
        prescription = get_active_prescription(db, current_user.id)
        if not prescription:
            raise HTTPException(
                status_code=404,
                detail="No active prescription found"
            )

        prescription_data = json.loads(prescription.prescription_data)
        now = datetime.now()
        current_meal = detect_current_meal_zone()

        # Define meal order
        meal_order = ["breakfast", "mid_morning", "lunch", "dinner", "snack"]
        current_index = meal_order.index(current_meal) if current_meal in meal_order else len(meal_order)

        # Process user responses
        user_responses = questionnaire_data.get("responses", {})
        warnings = []
        schedule_table = []

        # Collect all doses for safety validation
        daily_doses = []

        # Validate for multiple dangerous inputs
        high_dose_count = 0
        total_excess_units = 0

        for meal in meal_order:
            if meal not in prescription_data:
                continue

            insulin_info = prescription_data[meal]
            prescribed_dose = insulin_info.get("dose", 0)
            insulin_name = insulin_info.get("insulin", "Unknown")
            insulin_type = insulin_info.get("type", "rapid")
            onset = insulin_info.get("onset", 30)

            dose_status = "📋 Scheduled"
            advice = f"{prescribed_dose} units (Take as usual)"

            # Process if user provided input for this meal
            if meal in user_responses:
                response = user_responses[meal]
                taken = response.get("taken", False)
                actual_dose = response.get("actual_dose")
                meal_time_str = response.get("meal_time")

                if taken and actual_dose is not None:
                    # CRITICAL SAFETY VALIDATION
                    try:
                        dose_warnings = InsulinSafetyValidator.validate_single_dose(
                            insulin_type, actual_dose, meal
                        )
                        warnings.extend(dose_warnings)

                        # Add to daily doses for total validation
                        daily_doses.append({
                            'actual_dose': actual_dose,
                            'insulin_type': insulin_type,
                            'prescribed_dose': prescribed_dose
                        })

                    except DoseTooHighError as e:
                        logger.error(f"CRITICAL DOSE ERROR for user {current_user.id}: {str(e)}")
                        raise validation_exception(
                            f"DANGEROUS DOSE DETECTED: {str(e)}",
                            {"meal": meal, "dose": actual_dose, "user_id": current_user.id}
                        )
                    except ValidationError as e:
                        raise validation_exception(str(e))

                    # Dose was taken - validate amount
                    if actual_dose == prescribed_dose:
                        dose_status = "✅ Correct dose taken"
                        advice = f"Took {actual_dose} units as prescribed"
                    elif actual_dose > prescribed_dose:
                        excess = actual_dose - prescribed_dose
                        total_excess_units += excess
                        high_dose_count += 1
                        dose_status = f"⚠️ OVERDOSE WARNING"
                        advice = f"You took {actual_dose} units, which is {excess} units MORE than prescribed ({prescribed_dose}). Monitor blood sugar closely!"
                        warnings.append(f"🚨 {meal.upper()}: OVERDOSE of {excess} units detected!")
                    else:
                        dose_status = f"⚠️ Underdose"
                        advice = f"You took {actual_dose} units, which is LESS than prescribed ({prescribed_dose}). Monitor sugar levels."

                    # Log the dose
                    try:
                        log_dose(
                            db=db,
                            user_id=current_user.id,
                            prescription_id=prescription.id,
                            meal_time=meal,
                            insulin_name=insulin_name,
                            insulin_type=insulin_type,
                            prescribed_dose=prescribed_dose,
                            status="taken",
                            actual_dose=actual_dose,
                            actual_time=now
                        )
                        logger.info(f"Dose logged for user {current_user.id}: {meal} - {actual_dose} units")
                    except Exception as e:
                        logger.error(f"Failed to log dose for user {current_user.id}: {str(e)}")
                        warnings.append(f"Failed to log {meal} dose: {str(e)}")

                elif not taken and meal_time_str:
                    # Dose was missed - calculate adjustment
                    try:
                        meal_time = datetime.strptime(meal_time_str, "%H:%M")
                        meal_time = meal_time.replace(year=now.year, month=now.month, day=now.day)
                        gap_minutes = (now - meal_time).total_seconds() / 60
                        if gap_minutes < 0:
                            gap_minutes += 24 * 60

                        adj_dose, dose_advice = calculate_adjusted_dose(insulin_type, prescribed_dose, gap_minutes, onset)
                        dose_status = "❌ Missed dose"
                        advice = f"Missed dose handling → {adj_dose} units → {dose_advice}"

                        # Log the missed dose
                        try:
                            log_dose(
                                db=db,
                                user_id=current_user.id,
                                prescription_id=prescription.id,
                                meal_time=meal,
                                insulin_name=insulin_name,
                                insulin_type=insulin_type,
                                prescribed_dose=prescribed_dose,
                                status="missed",
                                actual_dose=None,
                                actual_time=meal_time
                            )
                        except Exception as e:
                            logger.error(f"Failed to log missed dose: {str(e)}")
                            warnings.append(f"Failed to log {meal} missed dose: {str(e)}")

                    except ValueError:
                        warnings.append(f"Invalid time format for {meal}: {meal_time_str}")
                        dose_status = "❌ Invalid input"
                        advice = "Please provide valid time format (HH:MM)"

            # Only show meals up to current time
            if meal_order.index(meal) <= current_index:
                schedule_table.append({
                    "meal": meal.capitalize(),
                    "insulin": insulin_name,
                    "prescribed_dose": prescribed_dose,
                    "status": dose_status,
                    "advice": advice
                })

        # CRITICAL SAFETY CHECK: Validate daily totals
        if daily_doses:
            try:
                daily_warnings = InsulinSafetyValidator.validate_daily_total(daily_doses)
                warnings.extend(daily_warnings)

                # Check for overdose patterns
                is_critical, overdose_warnings = InsulinSafetyValidator.check_overdose_pattern(daily_doses)
                if is_critical:
                    logger.critical(f"CRITICAL OVERDOSE PATTERN detected for user {current_user.id}")
                    warnings.extend(overdose_warnings)

            except Exception as e:
                logger.error(f"Error in daily safety validation: {str(e)}")

        # Generate critical warnings for multiple overdoses
        critical_warnings = []
        if high_dose_count >= 2:
            critical_warnings.append(f"🚨🚨 CRITICAL: Multiple overdoses detected ({high_dose_count} meals)!")
            critical_warnings.append(f"🚨🚨 Total excess insulin: {total_excess_units} units - CONTACT DOCTOR IMMEDIATELY!")
            critical_warnings.append("🚨🚨 Monitor blood sugar every 30 minutes!")
            logger.critical(f"Multiple overdoses detected for user {current_user.id}: {high_dose_count} overdoses, {total_excess_units} excess units")
        elif total_excess_units > 10:
            critical_warnings.append(f"🚨 WARNING: High excess insulin detected ({total_excess_units} units)")
            critical_warnings.append("🚨 Monitor blood sugar closely and have glucose tablets ready!")

        return {
            "current_time": now.strftime('%H:%M'),
            "current_zone": current_meal.upper(),
            "schedule": schedule_table,
            "warnings": warnings,
            "critical_warnings": critical_warnings,
            "summary": {
                "total_meals_processed": len([m for m in meal_order if m in user_responses]),
                "overdoses_detected": high_dose_count,
                "total_excess_units": total_excess_units,
                "requires_medical_attention": high_dose_count >= 2 or total_excess_units > 10
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in questionnaire processing: {str(e)}")
        raise internal_server_exception("Failed to process questionnaire")

@router.get("/doses/history")
def get_dose_history_consolidated(
    days: int = 7,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dose history with validation"""
    if days < 1 or days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 30"
        )

    dose_history = get_dose_history(db, current_user.id, days)
    return {
        "period_days": days,
        "total_entries": len(dose_history),
        "doses": dose_history
    }

@router.get("/template")
def get_questionnaire_template(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the prescription schedule template for questionnaire"""
    prescription = get_active_prescription(db, current_user.id)
    if not prescription:
        # Return default template if no prescription
        prescription_data = PRESCRIPTION_TEMPLATE
    else:
        prescription_data = json.loads(prescription.prescription_data)

    current_meal = detect_current_meal_zone()
    now = datetime.now()

    # Define meal order
    meal_order = ["breakfast", "mid_morning", "lunch", "dinner", "snack"]
    current_index = meal_order.index(current_meal) if current_meal in meal_order else len(meal_order)

    template = []
    for i, meal in enumerate(meal_order):
        if meal in prescription_data:
            dose_info = prescription_data[meal]
            template.append({
                "meal": meal.title(),
                "meal_time": meal,
                "insulin": dose_info.get("insulin", "Unknown"),
                "prescribed_dose": dose_info.get("dose", 0),
                "insulin_type": dose_info.get("type", "rapid"),
                "onset": dose_info.get("onset", 30),
                "is_past_or_current": i <= current_index,
                "example_input": {
                    "taken": True,
                    "actual_dose": dose_info.get("dose", 0),
                    "meal_time": "08:00"  # Example time
                }
            })

    return {
        "current_time": now.strftime('%H:%M'),
        "current_zone": current_meal.upper(),
        "template": template,
        "instructions": {
            "taken": "true if you took the dose, false if missed",
            "actual_dose": "number of units taken (required if taken=true)",
            "meal_time": "HH:MM format when you had the meal (required if taken=false)"
        },
        "warnings": [
            "⚠️ Entering multiple high doses will trigger critical warnings",
            "⚠️ System will alert if total excess insulin > 10 units",
            "⚠️ Multiple overdoses require immediate medical attention"
        ]
    }
