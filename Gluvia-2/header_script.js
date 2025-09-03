document.addEventListener("DOMContentLoaded", function() {
  const headerPlaceholder = document.getElementById("header-placeholder");
  
  if (headerPlaceholder) {
    fetch("header.html")
      .then(response => response.text())
      .then(data => {
        // Step 1: Inject the header HTML
        headerPlaceholder.innerHTML = data;
        
        // Step 2: Call the function to set the active class
        setActiveLink();
      })
      .catch(error => {
        console.error("Error loading the header:", error);
        headerPlaceholder.innerHTML = "<p>Error loading navigation bar.</p>";
      });
  }
});

function setActiveLink() {
  // Get the filename of the current page
  const currentPage = window.location.pathname.split("/").pop();
  
  // Find all the navigation links
  const navLinks = document.querySelectorAll(".section-bar a");
  
  // Loop through them to find the match
  navLinks.forEach(link => {
    const linkPage = link.getAttribute("href").split("/").pop();
    
    // If a link's destination matches the current page, add the 'active' class
    if (linkPage === currentPage) {
      link.classList.add("active");
    }
  });
}
