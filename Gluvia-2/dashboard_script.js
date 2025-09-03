//Navigate to prescriptions page
    document.getElementById("prescriptions").addEventListener("click", function () {
      window.location.href = "prescription.html"; 
    });

    //Handle file upload UI
    document.getElementById('prescriptionUpload').addEventListener('change', function() {
      const loader = document.getElementById('loader');
      const message = document.getElementById('uploadMessage');
      
      //Hide message and show loader
      message.style.display = 'none';
      loader.style.display = 'block';

      //Simulate an upload process
      setTimeout(() => {
        loader.style.display = 'none';
        message.style.display = 'block';
      }, 2000); //2-second upload simulation
    });