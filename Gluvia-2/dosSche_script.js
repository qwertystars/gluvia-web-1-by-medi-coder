 const prescriptionData = [
            {"Meal":"Breakfast","insulin":"Humalog","dose":10,"type":"Rapid-acting"},
            {"Meal":"Lunch","insulin":"Regular (R)","dose":15,"type":"Short-acting"},
            {"Meal":"Dinner","insulin":"Novolin N (NPH)","dose":20,"type":"Intermediate-acting"},
            {"Meal":"Bedtime","insulin":"Lantus","dose":18,"type":"Long-acting"},
            {"Meal":"Mixed Meal","insulin":"NovoMix 70/30","dose":12,"type":"Mixed"}
        ];

        const tableBody = document.getElementById("table-body");

        //Loop through the data and create a table row for each entry
        prescriptionData.forEach(row => {
            const tr = document.createElement("tr");
            
            //Define the order of keys to ensure correct column placement
            const keys = ["Meal", "insulin", "dose", "type"];

            for (const key of keys) {
                const td = document.createElement("td");
                td.textContent = row[key];
                tr.appendChild(td);
            }
            tableBody.appendChild(tr);
        });