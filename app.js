const YEARS_BACK = 8;
const currentYear = new Date().getFullYear();

const els = {
  genre: document.getElementById("genre"),
  minRating: document.getElementById("min-rating"),
  yearFrom: document.getElementById("year-from"),
  yearTo: document.getElementById("year-to"),
  kuOnly: document.getElementById("ku-only"),
  sortBy: document.getElementById("sort-by"),
  body: document.getElementById("results-body"),
  count: document.getElementById("result-count"),
  empty: document.getElementById("empty-state"),
  generatedAt: document.getElementById("generated-at"),
};

els.yearFrom.value = currentYear - YEARS_BACK;
els.yearTo.value = currentYear;

let books = [];

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function kuLabel(status) {
  if (status === true) return { text: "Yes", cls: "ku-yes" };
  if (status === false) return { text: "No", cls: "ku-no" };
  return { text: "Unknown", cls: "ku-unknown" };
}

function render() {
  const genre = els.genre.value;
  const minRating = parseFloat(els.minRating.value) || 0;
  const yearFrom = parseInt(els.yearFrom.value, 10) || 0;
  const yearTo = parseInt(els.yearTo.value, 10) || 9999;
  const kuOnly = els.kuOnly.checked;
  const sortBy = els.sortBy.value;

  let filtered = books.filter((b) => {
    if (genre !== "all" && !b.genres.includes(genre)) return false;
    if (b.rating < minRating) return false;
    if (b.pub_year < yearFrom || b.pub_year > yearTo) return false;
    if (kuOnly && b.ku_status !== true) return false;
    return true;
  });

  filtered.sort((a, b) =>
    sortBy === "year" ? b.pub_year - a.pub_year : b.rating - a.rating
  );

  els.body.innerHTML = "";
  for (const b of filtered) {
    const ku = kuLabel(b.ku_status);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><a href="${b.goodreads_url}" target="_blank" rel="noopener">${escapeHtml(b.title)}</a></td>
      <td>${escapeHtml(b.author)}</td>
      <td>${b.genres.map(escapeHtml).join(", ")}</td>
      <td>${b.rating.toFixed(2)}</td>
      <td>${b.pub_year}</td>
      <td><span class="ku-badge ${ku.cls}">${ku.text}</span></td>
    `;
    els.body.appendChild(tr);
  }

  els.count.textContent = `${filtered.length} book${filtered.length === 1 ? "" : "s"}`;
  els.empty.hidden = filtered.length !== 0;
  document.getElementById("results").hidden = filtered.length === 0;
}

async function init() {
  const res = await fetch("data.json");
  const data = await res.json();
  books = data.books;

  const generated = new Date(data.generated_at);
  els.generatedAt.textContent = `Data last refreshed: ${generated.toLocaleDateString()} — click a title to open it on Goodreads`;

  for (const el of [els.genre, els.minRating, els.yearFrom, els.yearTo, els.kuOnly, els.sortBy]) {
    el.addEventListener("input", render);
    el.addEventListener("change", render);
  }

  render();
}

init().catch((err) => {
  document.body.innerHTML += `<p class="meta">Couldn't load data.json — run scraper.py to generate it. (${err})</p>`;
});
