document.addEventListener("DOMContentLoaded", function() {
    // --- FROM YOUR FRIEND'S CODE: The Prescription "Database" ---
    const prescription = {
        breakfast: { insulin: "Humalog", dose: 10, type: "rapid", onset: 15 },
        lunch: { insulin: "Novolin N", dose: 15, type: "intermediate", onset: 90 },
        dinner: { insulin: "Lantus", dose: 20, type: "long", onset: 60 }
    };
    const mealOrder = ["breakfast", "lunch", "dinner"];
    
    // --- FROM YOUR CODE: UI Elements & State Management ---
    const container = document.getElementById('assistant-container');
    const initiateButton = document.getElementById('initiate-assistant-btn');
    let currentMealIndex = 0;
    let userData = {};

    if (initiateButton) {
        initiateButton.addEventListener('click', startAssistant);
    }

    // --- FROM YOUR FRIEND'S CODE: The Dose Calculation Logic ---
    function calculateDose(insulinType, fullDose, gapMinutes, onsetMinutes) {
        if (gapMinutes <= onsetMinutes) return [fullDose, "Take full dose now (within onset period)."];
        switch (insulinType) {
            case "rapid":
                if (gapMinutes <= 60) return [fullDose * 0.6, `Take partial dose (${(fullDose * 0.6).toFixed(1)} units).`];
                return [0, "Too late for rapid dose; monitor sugar closely."];
            case "intermediate":
                if (gapMinutes <= 240) return [fullDose * 0.75, `Take partial dose (${(fullDose * 0.75).toFixed(1)} units).`];
                return [0, "Missed dose; monitor sugar."];
            case "long":
                if (gapMinutes <= 480) return [fullDose * 0.5, `Take partial dose (${(fullDose * 0.5).toFixed(1)} units).`];
                return [fullDose, "Too late; take next scheduled dose and consult provider."];
            default:
                return [0, "Unknown insulin type."];
        }
    }

    // --- MERGED LOGIC: The Main Application Flow ---

    function startAssistant() {
        currentMealIndex = 0;
        userData = {};
        askMealTaken();
    }

    function askMealTaken() {
        if (currentMealIndex >= mealOrder.length) {
            showResults();
            return;
        }
        const meal = mealOrder[currentMealIndex];
        const mealLabel = meal.charAt(0).toUpperCase() + meal.slice(1);

        container.innerHTML = `
            <div class="assistant-message">Did you have your ${mealLabel}?</div>
            <div class="radio-options">
                <input type="radio" id="yes" name="mealTaken" value="yes"><label for="yes">Yes</label>
                <input type="radio" id="no" name="mealTaken" value="no"><label for="no">No</label>
            </div>
            <button id="continue-btn" class="option-btn">Continue</button>
        `;
        document.getElementById('continue-btn').addEventListener('click', handleMealTaken);
    }

    function handleMealTaken() {
        const choice = document.querySelector('input[name="mealTaken"]:checked');
        if (!choice) return alert('Please select an option.');
        
        const meal = mealOrder[currentMealIndex];
        userData[meal] = { mealTaken: choice.value };

        if (choice.value === 'yes') {
            askDoseTaken();
        } else {
            userData[meal].doseTaken = "no";
            showMessageAndProceed(getMissedMealHTML());
        }
    }

    function askDoseTaken() {
        const meal = mealOrder[currentMealIndex];
        const mealLabel = meal.charAt(0).toUpperCase() + meal.slice(1);
        container.innerHTML = `
            <div class="assistant-message">Did you take your insulin dose for ${mealLabel}?</div>
            <div class="radio-options">
                <input type="radio" id="yes" name="doseTaken" value="yes"><label for="yes">Yes</label>
                <input type="radio" id="no" name="doseTaken" value="no"><label for="no">No</label>
            </div>
            <button id="continue-btn" class="option-btn">Continue</button>
        `;
        document.getElementById('continue-btn').addEventListener('click', handleDoseTaken);
    }

    function handleDoseTaken() {
        const choice = document.querySelector('input[name="doseTaken"]:checked');
        if (!choice) return alert('Please select an option.');

        const meal = mealOrder[currentMealIndex];
        userData[meal].doseTaken = choice.value;

        if (choice.value === 'yes') {
            askDoseAmount();
        } else {
            askMealTime();
        }
    }

    function askDoseAmount() {
        const meal = mealOrder[currentMealIndex];
        const mealLabel = meal.charAt(0).toUpperCase() + meal.slice(1);
        const prescribedDose = prescription[meal].dose;
        container.innerHTML = `
            <div class="assistant-message">How many units did you take for ${mealLabel}?</div>
            <div class="prescribed-dose-hint">(Prescribed: ${prescribedDose} units)</div>
            <div>
                <input type="number" id="dose-input" class="dose-input" placeholder="Units">
                <button id="submit-dose-btn" class="option-btn">Submit</button>
            </div>
        `;
        document.getElementById('submit-dose-btn').addEventListener('click', handleDoseAmount);
    }
    
    function handleDoseAmount() {
        const doseTaken = document.getElementById('dose-input').value;
        if (!doseTaken) return alert("Please enter the number of units.");
        
        const meal = mealOrder[currentMealIndex];
        userData[meal].amt = parseInt(doseTaken, 10);
        
        const prescribedDose = prescription[meal].dose;
        let messageHTML = `<div class="assistant-message">Good job! You've logged your dose.</div>`; // Default message
        if (userData[meal].amt > prescribedDose) messageHTML = getOverdoseHTML();
        if (userData[meal].amt < prescribedDose) messageHTML = getUnderdoseHTML();
        
        showMessageAndProceed(messageHTML);
    }

    function askMealTime() {
        const meal = mealOrder[currentMealIndex];
        const mealLabel = meal.charAt(0).toUpperCase() + meal.slice(1);
        container.innerHTML = `
            <div class="assistant-message">What time did you have your ${mealLabel}?</div>
            <div>
                <input type="time" id="meal-time" class="time-input">
                <button id="submit-time-btn" class="option-btn">Submit Time</button>
            </div>
        `;
        document.getElementById('submit-time-btn').addEventListener('click', handleMealTime);
    }

    function handleMealTime() {
        const mealTime = document.getElementById('meal-time').value;
        if (!mealTime) return alert("Please enter the time of your meal.");

        const meal = mealOrder[currentMealIndex];
        userData[meal].mealTime = mealTime;
        showNextMeal();
    }

    function showMessageAndProceed(htmlContent) {
        container.innerHTML = htmlContent;
        setTimeout(showNextMeal, 5000); // Wait 5 seconds
    }

    function showNextMeal() {
        currentMealIndex++;
        askMealTaken();
    }

    function showResults() {
        let tableRows = '';
        mealOrder.forEach(meal => {
            const data = userData[meal] || {};
            const info = prescription[meal];
            let status = "Not logged.";

            if (data.mealTaken === "no") {
                status = `Meal skipped. Dose not taken.`;
            } else if (data.doseTaken === "yes") {
                const amt = data.amt;
                if (amt === info.dose) status = `✅ Correct dose taken (${amt} units).`;
                else if (amt > info.dose) status = `⚠ Overdose! Took ${amt} units.`;
                else status = `⚠ Underdose! Took ${amt} units.`;
            } else if (data.doseTaken === "no") {
                if (!data.mealTime) {
                    status = "⚠ Meal time not entered.";
                } else {
                    const [h, m] = data.mealTime.split(":").map(s => parseInt(s, 10));
                    const now = new Date();
                    const mealDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h || 0, m || 0, 0);
                    let gap = (now - mealDate) / 60000;
                    if (gap < 0) gap = 0; // Don't calculate for future times
                    const [adjDose, advice] = calculateDose(info.type, info.dose, gap, info.onset);
                    status = `Missed dose. Advice: ${advice}`;
                }
            }
            
            tableRows += `
                <tr>
                    <td>${meal.charAt(0).toUpperCase() + meal.slice(1)}</td>
                    <td>${info.insulin}</td>
                    <td>${info.dose} units</td>
                    <td class="status">${status}</td>
                </tr>
            `;
        });

        container.innerHTML = `
            <div class="results-container">
                <h2>Today's Insulin Log & Advice</h2>
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Meal</th>
                            <th>Insulin</th>
                            <th>Prescribed Dose</th>
                            <th>Status & Advice</th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        `;
    }

    // --- Using your original HTML/CSS for the alerts ---
    function getMissedMealHTML() { return `<div class="assistant-message">Okay, meal skipped. Dose not required.</div>`; }
    function getOverdoseHTML() { return `...`; } // (Your original Overdose HTML here)
    function getUnderdoseHTML() { return `...`; } // (Your original Underdose HTML here)
});