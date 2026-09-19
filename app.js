const YEARS_BACK = 8;
const currentYear = new Date().getFullYear();
const DISMISSED_KEY = "ku-finder-dismissed";

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
  hiddenToggle: document.getElementById("hidden-toggle"),
  hiddenToggleLink: document.getElementById("hidden-toggle-link"),
};

els.yearFrom.value = currentYear - YEARS_BACK;
els.yearTo.value = currentYear;

let books = [];
let showHidden = false;

function loadDismissed() {
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveDismissed(set) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...set]));
  } catch {
    // localStorage unavailable — dismissals just won't persist this session.
  }
}

let dismissed = loadDismissed();

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

  let matching = books.filter((b) => {
    if (genre !== "all" && !b.genres.includes(genre)) return false;
    if (b.rating < minRating) return false;
    if (b.pub_year < yearFrom || b.pub_year > yearTo) return false;
    if (kuOnly && b.ku_status !== true) return false;
    return true;
  });

  matching.sort((a, b) =>
    sortBy === "year" ? b.pub_year - a.pub_year : b.rating - a.rating
  );

  const hiddenCount = matching.filter((b) => dismissed.has(b.goodreads_url)).length;
  const visible = showHidden
    ? matching
    : matching.filter((b) => !dismissed.has(b.goodreads_url));

  els.body.innerHTML = "";
  for (const b of visible) {
    const ku = kuLabel(b.ku_status);
    const isDismissed = dismissed.has(b.goodreads_url);
    const tr = document.createElement("tr");
    if (isDismissed) tr.classList.add("dismissed-row");
    tr.innerHTML = `
      <td><a href="${b.goodreads_url}" target="_blank" rel="noopener">${escapeHtml(b.title)}</a></td>
      <td>${escapeHtml(b.author)}</td>
      <td>${b.genres.map(escapeHtml).join(", ")}</td>
      <td>${b.rating.toFixed(2)}</td>
      <td>${b.pub_year}</td>
      <td><span class="ku-badge ${ku.cls}">${ku.text}</span></td>
      <td><button type="button" class="dismiss-btn" data-url="${escapeHtml(b.goodreads_url)}">${isDismissed ? "Restore" : "Not interested"}</button></td>
    `;
    els.body.appendChild(tr);
  }

  // Backfill happens for free here: the table always shows every remaining
  // match, so dismissing one just leaves the next-best match already in view.
  els.count.textContent = `${visible.length} book${visible.length === 1 ? "" : "s"}`;
  els.empty.hidden = visible.length !== 0;
  document.getElementById("results").hidden = visible.length === 0;

  if (hiddenCount > 0) {
    els.hiddenToggle.hidden = false;
    els.hiddenToggleLink.textContent = showHidden
      ? `Hide the ${hiddenCount} you've dismissed`
      : `${hiddenCount} dismissed — show them`;
  } else {
    els.hiddenToggle.hidden = true;
  }
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

  els.body.addEventListener("click", (e) => {
    const btn = e.target.closest(".dismiss-btn");
    if (!btn) return;
    const url = btn.dataset.url;
    if (dismissed.has(url)) {
      dismissed.delete(url);
    } else {
      dismissed.add(url);
    }
    saveDismissed(dismissed);
    render();
  });

  els.hiddenToggleLink.addEventListener("click", (e) => {
    e.preventDefault();
    showHidden = !showHidden;
    render();
  });

  render();
}

init().catch((err) => {
  document.body.innerHTML += `<p class="meta">Couldn't load data.json — run scraper.py to generate it. (${err})</p>`;
});
