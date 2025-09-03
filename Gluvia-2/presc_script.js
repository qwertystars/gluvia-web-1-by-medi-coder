document.addEventListener("DOMContentLoaded", function () {
  const prescriptionList = document.getElementById("prescriptionList");
  const prescriptions = JSON.parse(localStorage.getItem("prescriptions")) || [];

  if (prescriptions.length === 0) {
    prescriptionList.innerHTML = "<p>No prescriptions uploaded yet.</p>";
  } else {
    prescriptions.forEach(file => {
      const div = document.createElement("div");
      div.className = "prescription-item";
      div.textContent = file;
      prescriptionList.appendChild(div);
    });
  }
});