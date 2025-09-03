function login() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();
  const error_msg = document.getElementById("error_msg");
  const success_msg = document.getElementById("success_msg");

  const demo_user = "root";
  const demo_pwd = "12345";

  if (username === demo_user && password === demo_pwd) {
    error_msg.style.display = "none";
    success_msg.style.display = "block";
    setTimeout(() => {
      window.location.href = "dashboard.html";
    }, 1500);
  } else {
    success_msg.style.display = "none";
    error_msg.style.display = "block";
  }
}