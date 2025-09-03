document.getElementById("signupForm").addEventListener("submit", function(e) {
    e.preventDefault();

    // Collect values
    let firstName = document.getElementById("firstName").value.trim();
    let lastName = document.getElementById("lastName").value.trim();
    let email = document.getElementById("email").value.trim();
    let username = document.getElementById("username").value.trim();
    let password = document.getElementById("password").value.trim();
    let confirmPassword = document.getElementById("confirmPassword").value.trim();

    // Validate password match
    if (password !== confirmPassword) {
        alert("Passwords do not match!");
        return;
    }

    // Save to localStorage
    let user = {
        firstName: firstName,
        lastName: lastName,
        email: email,
        username: username,
        password: password
    };
    localStorage.setItem("user", JSON.stringify(user));

    // Mark this as a new user
    localStorage.setItem("isNewUser", "true");

    // Redirect to dashboard
    window.location.href = "dashboard.html";
});
