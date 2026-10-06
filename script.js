document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const selector = link.getAttribute("href");
    if (!selector || selector === "#") return;
    const target = document.querySelector(selector);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const header = document.querySelector(".site-header");
let lastScrollY = window.scrollY;

window.addEventListener("scroll", () => {
  const currentScrollY = window.scrollY;
  header.classList.toggle("is-scrolled", currentScrollY > 12);
  if (currentScrollY > lastScrollY && currentScrollY > 120) {
    header.classList.add("is-hidden");
  } else {
    header.classList.remove("is-hidden");
  }
  lastScrollY = currentScrollY;
}, { passive: true });
