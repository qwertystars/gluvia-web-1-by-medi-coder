// corrected_prescription_flow.js
const prescription = {
  breakfast:   { insulin: "Humalog",     dose: 10, type: "rapid",        onset: 15 },
  mid_morning: { insulin: "Regular",     dose: 8,  type: "short",        onset: 30 },
  lunch:       { insulin: "Novolin N",   dose: 15, type: "intermediate", onset: 90 },
  dinner:      { insulin: "Lantus",      dose: 20, type: "long",         onset: 60 },
  snack:       { insulin: "Mix 70/30",   dose: 12, type: "mixed",        onset: 30 }
};

const mealOrder = ["breakfast", "mid_morning", "lunch", "dinner", "snack"];
let currentMealIndex = 0;
let userData = {};

// DOM elements (make sure these IDs exist in your HTML)
const questionText = document.getElementById("question-text");
const mealTakenSection = document.getElementById("meal-taken-section");
const doseTakenSection = document.getElementById("dose-taken-section");
const doseAmountSection = document.getElementById("dose-amount-section");
const mealTimeSection = document.getElementById("meal-time-section");
const resultSection = document.getElementById("result-section");
const questionSection = document.getElementById("question-section");

// helper: calculation logic (returns [doseToTake (number), advice (string)])
function calculateDose(insulinType, fullDose, gapMinutes, onsetMinutes) {
  // gapMinutes: minutes passed since scheduled time / meal time
  if (gapMinutes <= onsetMinutes) {
    // still within onset — take full dose
    return [fullDose, "Take full dose now (within onset period)."];
  }

  // after onset, choose partial or no dose depending on insulin type and gap
  switch (insulinType) {
    case "rapid":
      if (gapMinutes <= 60) return [fullDose * 0.6, `Take partial dose (${(fullDose * 0.6).toFixed(1)} units).`];
      return [0, "Too late for rapid dose; monitor sugar closely."];
    case "short":
      if (gapMinutes <= 120) return [fullDose * 0.5, `Take partial dose (${(fullDose * 0.5).toFixed(1)} units).`];
      return [0, "Too late for short insulin; monitor sugar."];
    case "intermediate":
      if (gapMinutes <= 240) return [fullDose * 0.75, `Take partial dose (${(fullDose * 0.75).toFixed(1)} units).`];
      return [0, "Missed dose; monitor sugar and contact provider if needed."];
    case "long":
      if (gapMinutes <= 480) return [fullDose * 0.5, `Take partial dose (${(fullDose * 0.5).toFixed(1)} units).`];
      // For very long-acting, sometimes continuing next scheduled dose is recommended; this is generic advice
      return [fullDose, "Too late for scheduled long dose; follow next scheduled dose and consult provider."];
    case "mixed":
      if (gapMinutes <= 180) return [fullDose * 0.7, `Take partial dose (${(fullDose * 0.7).toFixed(1)} units).`];
      return [0, "Too late for mixed dose; monitor sugar."];
    default:
      return [0, "Unknown insulin type — follow provider guidance."];
  }
}

// Display question for current meal
function showMealQuestion() {
  if (currentMealIndex >= mealOrder.length) {
    showResults();
    return;
  }

  const meal = mealOrder[currentMealIndex];
  const info = prescription[meal];
  const mealLabel = meal.replace("_", " ").toUpperCase();
  if (questionText) {
    questionText.textContent = `${mealLabel} (${info.insulin} — ${info.dose} units)`;
  }

  // Show only the first step (meal taken)
  if (mealTakenSection) mealTakenSection.style.display = "block";
  if (doseTakenSection) doseTakenSection.style.display = "none";
  if (doseAmountSection) doseAmountSection.style.display = "none";
  if (mealTimeSection) mealTimeSection.style.display = "none";

  // Ensure result section hidden
  if (resultSection) resultSection.style.display = "none";
  if (questionSection) questionSection.style.display = "block";
}

// Called when user clicks next/submit for the current visible section
function nextStep() {
  const meal = mealOrder[currentMealIndex];
  const info = prescription[meal];

  // 1) Meal taken section
  if (mealTakenSection && mealTakenSection.style.display === "block") {
    const sel = document.getElementById("meal-taken");
    const mealTaken = sel ? sel.value : "no";
    userData[meal] = { mealTaken };

    if (mealTaken === "no") {
      userData[meal].doseTaken = "no";
      showNextMeal();
      return;
    } else {
      // go to dose taken section
      mealTakenSection.style.display = "none";
      if (doseTakenSection) doseTakenSection.style.display = "block";
      return;
    }
  }

  // 2) Dose taken section
  if (doseTakenSection && doseTakenSection.style.display === "block") {
    const sel = document.getElementById("dose-taken");
    const doseTaken = sel ? sel.value : "no";
    userData[meal].doseTaken = doseTaken;

    doseTakenSection.style.display = "none";

    if (doseTaken === "yes") {
      if (doseAmountSection) doseAmountSection.style.display = "block";
    } else {
      if (mealTimeSection) mealTimeSection.style.display = "block";
    }
    return;
  }

  // 3) Dose amount provided
  if (doseAmountSection && doseAmountSection.style.display === "block") {
    const amtInput = document.getElementById("dose-amount");
    const amt = amtInput ? parseFloat(amtInput.value) : NaN;
    userData[meal].amt = isNaN(amt) ? 0 : amt;

    // evaluate over/under dose tips
    const fullDose = info.dose;
    let tipHTML = "";
    let showTip = false;

    if (userData[meal].amt > fullDose) {
      tipHTML = `
        <div class="tip-card" style="background:#ffefef;border:1px solid #f0a0a0;padding:12px;margin-bottom:12px;border-radius:8px;">
          <strong style="color:#b00020;">⚠ Overdose Alert:</strong>
          <ul style="margin-top:6px;padding-left:18px;color:#333;">
            <li>Check blood sugar immediately.</li>
            <li>If low (&lt;70 mg/dL), consume fast-acting carbs (juice, glucose tablets).</li>
            <li>Do not take the next insulin dose until advised by provider.</li>
            <li>Contact healthcare provider if symptoms or uncertainty.</li>
          </ul>
        </div>`;
      showTip = true;
    } else if (userData[meal].amt < fullDose) {
      tipHTML = `
        <div class="tip-card" style="background:#fff8e1;border:1px solid #ffe8a1;padding:12px;margin-bottom:12px;border-radius:8px;">
          <strong style="color:#8a6d00;">⚠ Underdose Alert:</strong>
          <ol style="margin-top:6px;padding-left:18px;color:#333;">
            <li>Check blood sugar as soon as possible.</li>
            <li>If high, follow provider guidance for correction.</li>
            <li>Do not double next dose without advice.</li>
            <li>Monitor blood sugar frequently for next hours.</li>
          </ol>
        </div>`;
      showTip = true;
    }

    doseAmountSection.style.display = "none";

    if (showTip) {
      const container = document.querySelector(".container") || document.body;
      const tipDiv = document.createElement("div");
      tipDiv.innerHTML = tipHTML;
      container.insertBefore(tipDiv, questionSection || container.firstChild);

      // Show for 6 seconds then remove and move on
      setTimeout(() => {
        tipDiv.remove();
        showNextMeal();
      }, 6000);
    } else {
      showNextMeal();
    }
    return;
  }

  // 4) Meal time input section (when user says dose not taken)
  if (mealTimeSection && mealTimeSection.style.display === "block") {
    // prefer an input field if you have one; otherwise fallback to prompt
    const timeInput = document.getElementById("meal-time-input");
    let mealTimeInput = "";
    if (timeInput) {
      mealTimeInput = timeInput.value.trim();
    } else {
      mealTimeInput = prompt("Enter current time in HH:MM format (24h):");
    }

    userData[meal].mealTime = mealTimeInput;
    mealTimeSection.style.display = "none";
    showNextMeal();
    return;
  }

  // default fallback (shouldn't get here)
  showNextMeal();
}

// move to next meal and show its question
function showNextMeal() {
  currentMealIndex++;
  showMealQuestion();
}

// show final table of results
function showResults() {
  const tbody = document.querySelector("#result-table tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  mealOrder.forEach(meal => {
    const data = userData[meal] || {};
    const info = prescription[meal];
    const insulin = info.insulin;
    const dose = info.dose;
    const type = info.type;
    const onset = info.onset;

    let status = "";

    if (!Object.keys(data).length) {
      // never answered
      status = `${dose} units (Take as usual)`;
    } else if (data.mealTaken === "no") {
      status = `Take your meal first and then ${insulin} (${dose} units).`;
    } else if (data.doseTaken === "yes") {
      const amt = data.amt;
      if (amt === dose) status = "✅ Correct dose taken.";
      else if (amt > dose) status = `⚠ Overdose! You took ${amt} units.`;
      else status = `⚠ Underdose! You took ${amt} units.`;
    } else {
      // doseTaken === "no" (user didn't take) but we have mealTime
      if (!data.mealTime) {
        status = "⚠ Meal time not entered.";
      } else {
        // compute gap in minutes from the given mealTime to now
        const [h, m] = data.mealTime.split(":").map(s => parseInt(s, 10));
        const now = new Date();
        const mealDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h || 0, m || 0, 0);
        let gap = (now - mealDate) / 60000; // minutes
        if (gap < 0) gap += 24 * 60; // if time refers to previous day
        const [adjDose, advice] = calculateDose(type, dose, gap, onset);
        status = `Missed dose → ${adjDose.toFixed(1)} units → ${advice}`;
      }
    }

    const row = document.createElement("tr");
    // create cells
    const c1 = document.createElement("td"); c1.textContent = meal.replace("_", " ").toUpperCase();
    const c2 = document.createElement("td"); c2.textContent = insulin;
    const c3 = document.createElement("td"); c3.textContent = dose;
    const c4 = document.createElement("td"); c4.className = "status"; c4.innerHTML = status;

    row.appendChild(c1);
    row.appendChild(c2);
    row.appendChild(c3);
    row.appendChild(c4);
    tbody.appendChild(row);
  });

  if (questionSection) questionSection.style.display = "none";
  if (resultSection) resultSection.style.display = "block";
}

// kick off
showMealQuestion();

// If you have a "Next" button in UI, wire it to call nextStep(), e.g.:
// document.getElementById('next-btn').addEventListener('click', nextStep);