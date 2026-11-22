// Homepage disclaimer expand/collapse.

const toggle = document.querySelector("#disclaimer-toggle");
const detail = document.querySelector("#disclaimer-detail");

function setExpanded(open) {
  toggle.setAttribute("aria-expanded", String(open));
  detail.dataset.open = String(open);
  detail.setAttribute("aria-hidden", String(!open));
  toggle.textContent = open ? "Sembunyikan" : "Baca selengkapnya";
}

if (toggle && detail) {
  toggle.addEventListener("click", () => {
    setExpanded(toggle.getAttribute("aria-expanded") !== "true");
  });
}
