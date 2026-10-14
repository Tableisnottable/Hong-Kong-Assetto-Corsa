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

// ---- Bus catalog (buses.html) ----
(function () {
  const listEl = document.getElementById("bus-list");
  if (!listEl || typeof window.BUS_DATA === "undefined") return;

  const data = window.BUS_DATA;
  const countEl = document.getElementById("catalog-count");
  const filterEl = document.getElementById("operator-filter");
  const sortEl = document.getElementById("sort-select");

  let activeOp = "ALL";

  function render() {
    const sort = sortEl.value;
    let operators = data.operators.filter(
      (op) => activeOp === "ALL" || op.code === activeOp
    );
    if (activeOp === "ALL") {
      operators = operators.filter((op) => op.total > 0);
    }

    // Render operator filter chips (once)
    if (!filterEl.dataset.built) {
      filterEl.dataset.built = "1";
      const allChips = [filterEl.querySelector("button")];
      const opChips = data.operators
        .filter((op) => op.total > 0)
        .map((op) => {
          const b = document.createElement("button");
          b.className = "bus-chip";
          b.dataset.op = op.code;
          b.textContent = `${op.name_tc} ${op.code}`;
          b.addEventListener("click", () => {
            activeOp = b.dataset.op;
            filterEl.querySelectorAll(".bus-chip").forEach((c) => c.classList.toggle("active", c === b));
            render();
          });
          return b;
        });
      allChips[0].addEventListener("click", () => {
        activeOp = "ALL";
        filterEl.querySelectorAll(".bus-chip").forEach((c) => c.classList.toggle("active", c === allChips[0]));
        render();
      });
      opChips.forEach((c) => filterEl.appendChild(c));
    }

    let html = "";
    for (const op of operators) {
      const models = [...op.models].sort((a, b) =>
        sort === "count" ? b.count - a.count : a.model.localeCompare(b.model, "zh-Hant")
      );
      const rows = models
        .map(
          (m) => `
          <div class="bus-row">
            <span class="bus-prefix">${m.prefix || "—"}</span>
            <span class="bus-model">${m.model}</span>
            <span class="bus-count">${m.count}</span>
          </div>`
        )
        .join("");
      html += `
        <div class="bus-operator">
          <div class="bus-operator-head">
            <h2>${op.name_tc} <em>${op.code}</em></h2>
            <span class="bus-operator-total">${op.total} 部</span>
          </div>
          <div class="bus-table">
            <div class="bus-row bus-row-head">
              <span class="bus-prefix">車隊編號</span>
              <span class="bus-model">型號</span>
              <span class="bus-count">數量</span>
            </div>
            ${rows}
          </div>
        </div>`;
    }
    listEl.innerHTML = html || '<p class="map-footnote">沒有符合的資料。</p>';
    if (countEl) {
      const totalModels = operators.reduce((n, op) => n + op.models.length, 0);
      const totalFleet = operators.reduce((n, op) => n + op.total, 0);
      countEl.textContent = `${operators.length} 營辦商 · ${totalModels} 型號 · ${totalFleet} 部`;
    }
  }

  if (sortEl) sortEl.addEventListener("change", render);
  render();
})();
