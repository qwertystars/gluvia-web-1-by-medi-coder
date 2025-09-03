# Gluvia Consolidated Routes Guide

## 🎯 Route Consolidation Summary

**BEFORE**: 12+ redundant endpoints across multiple files  
**AFTER**: 6 powerful, consolidated endpoints with comprehensive insulin management

---

## 🚨 CRITICAL WARNING SYSTEM

The system now implements **MULTI-OVERDOSE DETECTION** based on your prescription logic:

- **2+ overdoses**: 🚨🚨 CRITICAL WARNING - Contact doctor immediately!
- **>10 excess units**: 🚨 HIGH RISK - Monitor blood sugar every 30 minutes
- **Real-time alerts**: System tracks cumulative excess insulin across all meals

---

## 📋 New Consolidated Endpoints

### 1. **GET /prescriptions/template** 
Get questionnaire template with instructions
```json
{
  "current_time": "14:30",
  "current_zone": "LUNCH",
  "template": [
    {
      "meal": "Breakfast",
      "meal_time": "breakfast",
      "insulin": "Humalog",
      "prescribed_dose": 10,
      "insulin_type": "rapid",
      "onset": 15,
      "is_past_or_current": true
    }
  ],
  "warnings": [
    "⚠️ Entering multiple high doses will trigger critical warnings",
    "⚠️ System will alert if total excess insulin > 10 units"
  ]
}
```

### 2. **POST /prescriptions/daily-questionnaire** (MAIN ENDPOINT)
Process daily insulin questionnaire with comprehensive logic

**Input Example:**
```json
{
  "responses": {
    "breakfast": {
      "taken": true,
      "actual_dose": 15,
      "meal_time": "08:00"
    },
    "lunch": {
      "taken": false,
      "meal_time": "13:30"
    },
    "dinner": {
      "taken": true,
      "actual_dose": 25
    }
  }
}
```

**Output with Warnings:**
```json
{
  "current_time": "15:45",
  "current_zone": "LUNCH",
  "schedule": [
    {
      "meal": "Breakfast",
      "insulin": "Humalog",
      "prescribed_dose": 10,
      "status": "⚠️ OVERDOSE WARNING",
      "advice": "You took 15 units, which is 5 units MORE than prescribed (10). Monitor blood sugar closely!"
    }
  ],
  "warnings": [
    "🚨 BREAKFAST: OVERDOSE of 5 units detected!",
    "🚨 DINNER: OVERDOSE of 5 units detected!"
  ],
  "critical_warnings": [
    "🚨🚨 CRITICAL: Multiple overdoses detected (2 meals)!",
    "🚨🚨 Total excess insulin: 10 units - CONTACT DOCTOR IMMEDIATELY!",
    "🚨🚨 Monitor blood sugar every 30 minutes!"
  ],
  "summary": {
    "total_meals_processed": 3,
    "overdoses_detected": 2,
    "total_excess_units": 10,
    "requires_medical_attention": true
  }
}
```

### 3. **GET /prescriptions/status**
Get comprehensive status including current meal zone and today's activity
```json
{
  "current_time": "14:30",
  "current_zone": "LUNCH",
  "prescription_data": { /* full prescription */ },
  "today_doses": [ /* today's dose history */ ],
  "meal_options": ["breakfast", "mid_morning", "lunch", "dinner", "snack"]
}
```

### 4. **GET /prescriptions/doses/history?days=7**
Get dose history with validation (1-30 days)

### 5. **POST /prescriptions/** 
Create/update prescriptions

### 6. **GET /prescriptions/active**
Get active prescription information

---

## 🧮 Insulin Calculation Logic (Per Your Code)

### Onset-Based Adjustments:
- **Within onset time**: Full dose
- **After onset**: Reduced dose based on insulin type

### Insulin Types & Missed Dose Logic:
```
RAPID (Humalog, 15min onset):
  ≤60min late: 60% of dose
  >60min: Too late, monitor blood sugar

SHORT (Regular, 30min onset):
  ≤120min late: 50% of dose  
  >120min: Too late, monitor blood sugar

INTERMEDIATE (Novolin N, 90min onset):
  ≤240min late: 75% of dose
  >240min: Missed, monitor closely

LONG (Lantus, 60min onset):
  ≤480min late: 50% of dose
  >480min: Continue next scheduled dose

MIXED (Mix 70/30, 30min onset):
  ≤180min late: 70% of dose
  >180min: Too late, monitor blood sugar
```

---

## 🕐 Meal Zone Detection
```
06:00-10:00: BREAKFAST
10:00-12:00: MID_MORNING  
12:00-18:00: LUNCH
18:00-22:00: DINNER
22:00-06:00: SNACK
```

---

## 🎯 Usage Examples

### Basic Daily Check-in:
1. **GET** `/prescriptions/template` - Get today's schedule
2. **POST** `/prescriptions/daily-questionnaire` - Submit responses
3. **Review warnings** - Follow critical alerts if any

### Multiple Overdose Scenario:
```json
{
  "responses": {
    "breakfast": {"taken": true, "actual_dose": 18},
    "lunch": {"taken": true, "actual_dose": 22},
    "dinner": {"taken": true, "actual_dose": 28}
  }
}
```
**Result**: 🚨🚨 CRITICAL ALERT - 18 excess units detected!

---

## 🔧 PowerShell Testing Commands

```powershell
# Test consolidated routes import
cd "C:\Users\srija\PycharmProjects\Gluvia"
python -c "from routes.consolidated_routes import router; print('✅ Routes working')"

# Test main app with new routes  
python -c "from main import app; print('✅ App loaded successfully')"

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📁 File Changes Made

### ✅ Created:
- `routes/consolidated_routes.py` - Main consolidated endpoints
- `routes/backup/old_prescription_routes.py` - Backup of old routes

### ✅ Updated:
- `main.py` - Now uses consolidated routes
- Route imports simplified and streamlined

### 🗑️ Deprecated (backed up):
- Multiple redundant prescription endpoints
- Duplicate dose logging endpoints  
- Overlapping questionnaire routes

---

## 🚨 Safety Features

1. **Multi-Overdose Detection**: Prevents dangerous insulin combinations
2. **Cumulative Tracking**: Monitors total excess units across meals
3. **Medical Alert Triggers**: Automatic warnings for dangerous situations
4. **Input Validation**: Comprehensive error checking and user guidance
5. **Meal Timing Logic**: Accounts for insulin onset times and effectiveness windows

The system now provides enterprise-level safety monitoring while maintaining simplicity for daily use!
