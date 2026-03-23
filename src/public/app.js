/*
 * app.js — OpportunityFinder Frontend (Vercel Edition)
 *
 * API calls go to /api/* which Vercel routes to serverless functions.
 * No hardcoded localhost — works both locally and deployed.
 */

// ═══════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════

let currentKeywords = [];
let currentResults = [];
let currentSearchId = "";
let currentFilter = "all";
let editingKeywords = false;

// Auth state
let supabaseClient = null;
let currentUser    = null;
let currentToken   = null;
let authMode       = "login";

// ═══════════════════════════════════════════
//  PAGE ROUTER
// ═══════════════════════════════════════════

function showPage(pageId) {
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  const page = document.getElementById(`page-${pageId}`);
  if (page) {
    page.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (pageId === "bookmarks") loadBookmarks();
  if (pageId === "history") loadHistory();
}

function quickPick(topic) {
  document.getElementById("input-topic").value = topic;
  document.getElementById("input-topic").focus();
}

// ═══════════════════════════════════════════
//  LOADING STEP ANIMATION
// ═══════════════════════════════════════════

function setStep(stepNum) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`step-${i}`);
    if (!el) continue;
    el.classList.remove("active", "done");
    el.querySelector(".step-dot").classList.remove("active");

    if (i < stepNum) {
      el.classList.add("done");
    } else if (i === stepNum) {
      el.classList.add("active");
      el.querySelector(".step-dot").classList.add("active");
    }
  }
}

// ═══════════════════════════════════════════
//  MAIN SEARCH
// ═══════════════════════════════════════════

async function handleSearch() {
  const topic = document.getElementById("input-topic").value.trim();
  if (!topic) {
    document.getElementById("input-topic").focus();
    return;
  }

  const description = document.getElementById("input-description").value.trim();
  const level = document.getElementById("input-level").value;
  const country = document.getElementById("input-country").value.trim();
  const budget = document.getElementById("input-budget").value;
  const format = document.getElementById("input-format").value;

  // Gather checked opportunity types
  const checkedTypes = Array.from(
    document.querySelectorAll('.checkbox-grid input[type="checkbox"]:checked')
  ).map((cb) => cb.value);

  // Build goals string
  const goalParts = [];
  if (checkedTypes.length > 0) goalParts.push(`Looking for: ${checkedTypes.join(", ")}`);
  if (format !== "any") goalParts.push(`Format: ${format}`);
  if (description) goalParts.push(description);
  const goals = goalParts.join(". ");

  // Disable button
  const btn = document.getElementById("btn-search");
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Searching...';

  // Show loading with steps
  showPage("loading");
  document.getElementById("loading-text").textContent = "Analyzing your profile...";
  document.getElementById("loading-sub").textContent = topic;
  setStep(1);

  try {
    // Animate steps while waiting
    setTimeout(() => setStep(2), 800);
    setTimeout(() => {
      setStep(3);
      document.getElementById("loading-text").textContent = "Crawling for opportunities...";
    }, 2000);

    const resp = await fetch("/api/search", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ topic, level, country, budget, goals }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${resp.status}`);
    }

    setStep(4);
    document.getElementById("loading-text").textContent = "Classifying results...";

    const data = await resp.json();

    // Small delay so step 4 is visible
    await new Promise((r) => setTimeout(r, 500));

    currentSearchId = data.search_id;
    currentKeywords = data.keywords || [];
    currentResults = data.results || [];
    currentFilter = "all";
    editingKeywords = false;

    renderResults(topic);
    showPage("results");
  } catch (err) {
    console.error("Search failed:", err);
    showPage("landing");
    showError(
      err.message.includes("Failed to fetch")
        ? "Cannot reach the server. Make sure Vercel functions are deployed and GROQ_API_KEY + SERPER_API_KEY are set in Vercel Environment Variables."
        : err.message
    );
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">⟐</span> Find Opportunities';
  }
}

// ═══════════════════════════════════════════
//  RE-SEARCH
// ═══════════════════════════════════════════

async function reSearch() {
  if (currentKeywords.length === 0) return;

  showPage("loading");
  document.getElementById("loading-text").textContent = "Re-searching with updated keywords...";
  document.getElementById("loading-sub").textContent = `${currentKeywords.length} keywords`;
  setStep(3);

  try {
    const resp = await fetch("/api/refine", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ keywords: currentKeywords, search_id: currentSearchId }),
    });

    if (!resp.ok) throw new Error(`Server error ${resp.status}`);

    setStep(4);
    await new Promise((r) => setTimeout(r, 400));

    const data = await resp.json();
    currentSearchId = data.search_id;
    currentKeywords = data.keywords || currentKeywords;
    currentResults = data.results || [];
    currentFilter = "all";
    editingKeywords = false;

    renderResults("Refined Search");
    showPage("results");
  } catch (err) {
    console.error("Re-search failed:", err);
    showPage("results");
    showError("Re-search failed. " + err.message);
  }
}

// ═══════════════════════════════════════════
//  RENDER
// ═══════════════════════════════════════════

function renderResults(title) {
  document.getElementById("results-title").textContent = title;
  renderKeywords();
  renderFilters();
  renderResultCards();
}

function renderKeywords() {
  const container = document.getElementById("keywords-tags");
  container.innerHTML = currentKeywords
    .map(
      (kw, i) =>
        `<span class="kw-tag">${esc(kw)}<button class="remove-kw" onclick="event.stopPropagation();removeKeyword(${i})" title="Remove">×</button></span>`
    )
    .join("");

  document.getElementById("keywords-editor").style.display = editingKeywords ? "block" : "none";
  const btn = document.getElementById("btn-edit-kw");
  btn.textContent = editingKeywords ? "Done Editing" : "Edit Keywords";
  btn.classList.toggle("active", editingKeywords);
}

function renderFilters() {
  const types = [...new Set(currentResults.map((r) => r.type || "opportunity"))];
  const container = document.getElementById("filter-chips");
  let html = `<button class="filter-chip ${currentFilter === "all" ? "active" : ""}" onclick="setFilter('all')">All</button>`;
  types.forEach((t) => {
    html += `<button class="filter-chip ${currentFilter === t ? "active" : ""}" onclick="setFilter('${t}')">${t}</button>`;
  });
  container.innerHTML = html;
}

function renderResultCards() {
  const filtered =
    currentFilter === "all"
      ? currentResults
      : currentResults.filter((r) => r.type === currentFilter);

  document.getElementById("results-count").textContent =
    `${filtered.length} opportunit${filtered.length === 1 ? "y" : "ies"}`;

  const container = document.getElementById("results-list");
  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">No results found. Try editing keywords and re-searching!</div>`;
    return;
  }

  container.innerHTML = filtered
    .map((r, i) => {
      const domain = getDomain(r.url);
      const type = r.type || "opportunity";
      return `
      <div class="result-card" style="animation-delay:${i * 0.04}s"
           onclick="window.open('${escAttr(r.url)}','_blank','noopener')">
        <div class="result-card-top">
          <span class="result-type-badge badge-${type}">${type}</span>
          <button class="result-bookmark-btn" onclick="event.stopPropagation();bookmarkResult(${i})" title="Save">☆</button>
        </div>
        <div class="result-domain">${esc(domain)}</div>
        <h3>${esc(r.title)}</h3>
        <p>${esc(r.snippet)}</p>
        <span class="visit-link">Visit →</span>
      </div>`;
    })
    .join("");
}

function setFilter(type) {
  currentFilter = type;
  renderFilters();
  renderResultCards();
}

// ═══════════════════════════════════════════
//  KEYWORD EDITING
// ═══════════════════════════════════════════

function toggleKeywordEdit() {
  editingKeywords = !editingKeywords;
  renderKeywords();
  if (editingKeywords) setTimeout(() => document.getElementById("input-new-kw")?.focus(), 100);
}

function removeKeyword(i) {
  currentKeywords.splice(i, 1);
  renderKeywords();
}

function addKeyword() {
  const input = document.getElementById("input-new-kw");
  const val = input.value.trim();
  if (val) {
    currentKeywords.push(val);
    input.value = "";
    renderKeywords();
  }
}

// ═══════════════════════════════════════════
//  BOOKMARKS
// ═══════════════════════════════════════════

async function bookmarkResult(index) {
  // Prompt login if not authenticated
  if (!currentUser) {
    showAuthModal();
    return;
  }

  const filtered =
    currentFilter === "all"
      ? currentResults
      : currentResults.filter((r) => r.type === currentFilter);
  const r = filtered[index];
  if (!r) return;

  try {
    await fetch("/api/bookmarks", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        result_id: r.result_id || "",
        title: r.title,
        url: r.url,
        snippet: r.snippet,
        type: r.type,
      }),
    });

    const cards = document.querySelectorAll(".result-card");
    if (cards[index]) {
      const btn = cards[index].querySelector(".result-bookmark-btn");
      if (btn) {
        btn.textContent = "★";
        btn.classList.add("bookmarked");
      }
    }
  } catch (err) {
    console.error("Bookmark failed:", err);
  }
}

async function loadBookmarks() {
  const container = document.getElementById("bookmarks-list");

  if (!currentUser) {
    container.innerHTML = '<p class="empty-state">Please <a href="#" onclick="showAuthModal()">login</a> to view your saved opportunities.</p>';
    return;
  }

  try {
    const resp = await fetch("/api/bookmarks", { headers: authHeaders() });
    const data = await resp.json();
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No bookmarks yet. Search and save the ones you like!</p>';
      return;
    }
    container.innerHTML = data
      .map(
        (b, i) => `
      <div class="result-card" style="animation-delay:${i * 0.04}s"
           onclick="window.open('${escAttr(b.url)}','_blank','noopener')">
        <div class="result-card-top">
          <span class="result-type-badge badge-${b.opportunity_type || "opportunity"}">${b.opportunity_type || "opportunity"}</span>
          <button class="result-bookmark-btn bookmarked" onclick="event.stopPropagation();removeBookmarkUI('${b.id}')" title="Remove">★</button>
        </div>
        <h3>${esc(b.title)}</h3>
        <p>${esc(b.snippet)}</p>
        <span class="visit-link">Visit →</span>
      </div>`
      )
      .join("");
  } catch {
    container.innerHTML = '<p class="empty-state">Could not load bookmarks.</p>';
  }
}

async function removeBookmarkUI(id) {
  try {
    await fetch(`/api/bookmarks?id=${id}`, { method: "DELETE", headers: authHeaders() });
    loadBookmarks();
  } catch (err) {
    console.error(err);
  }
}

// ═══════════════════════════════════════════
//  HISTORY
// ═══════════════════════════════════════════

async function loadHistory() {
  const container = document.getElementById("history-list");

  if (!currentUser) {
    container.innerHTML = '<p class="empty-state">Please <a href="#" onclick="showAuthModal()">login</a> to view your search history.</p>';
    return;
  }

  try {
    const resp = await fetch("/api/history", { headers: authHeaders() });
    const data = await resp.json();
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No searches yet.</p>';
      return;
    }
    container.innerHTML = data
      .map(
        (s) => `
      <div class="history-card" onclick="quickRerun('${escAttr(s.topic)}')">
        <div class="hist-topic">${esc(s.topic)}</div>
        <div class="hist-meta">
          ${s.level ? s.level + " · " : ""}${s.country ? s.country + " · " : ""}${s.budget || ""}
          ${s.created_at ? " · " + new Date(s.created_at).toLocaleDateString() : ""}
        </div>
      </div>`
      )
      .join("");
  } catch {
    container.innerHTML = '<p class="empty-state">Could not load history.</p>';
  }
}

function quickRerun(topic) {
  if (topic && topic !== "(refined search)") {
    document.getElementById("input-topic").value = topic;
    showPage("landing");
  }
}

// ═══════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════

function showAuthModal() {
  document.getElementById("auth-overlay").style.display = "flex";
  setTimeout(() => document.getElementById("auth-email").focus(), 50);
}

function closeAuthModal() {
  document.getElementById("auth-overlay").style.display = "none";
  document.getElementById("auth-message").style.display = "none";
  document.getElementById("auth-email").value = "";
  document.getElementById("auth-password").value = "";
}

function switchAuthTab(mode) {
  authMode = mode;
  document.getElementById("auth-submit").textContent = mode === "login" ? "Login" : "Sign Up";
  document.getElementById("tab-login").style.borderBottomColor  = mode === "login"  ? "#2563eb" : "transparent";
  document.getElementById("tab-signup").style.borderBottomColor = mode === "signup" ? "#2563eb" : "transparent";
}

async function handleAuthSubmit() {
  const email    = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;
  const msgEl    = document.getElementById("auth-message");

  if (!email || !password) {
    msgEl.textContent = "Please enter your email and password.";
    msgEl.style.display = "block";
    return;
  }

  const btn = document.getElementById("auth-submit");
  btn.textContent = "Please wait...";
  btn.disabled = true;

  try {
    const { error } = authMode === "login"
      ? await supabaseClient.auth.signInWithPassword({ email, password })
      : await supabaseClient.auth.signUp({ email, password });

    if (error) {
      msgEl.textContent = error.message;
      msgEl.style.display = "block";
    } else {
      closeAuthModal();
    }
  } catch (err) {
    msgEl.textContent = "Something went wrong. Try again.";
    msgEl.style.display = "block";
  } finally {
    btn.textContent = authMode === "login" ? "Login" : "Sign Up";
    btn.disabled = false;
  }
}

async function handleLogout() {
  await supabaseClient.auth.signOut();
}

function updateAuthUI(loggedIn) {
  document.getElementById("btn-login").style.display  = loggedIn ? "none" : "";
  document.getElementById("btn-logout").style.display = loggedIn ? "" : "none";
}

// ═══════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (currentToken) h["Authorization"] = `Bearer ${currentToken}`;
  return h;
}

function showError(msg) {
  const active = document.querySelector(".page.active");
  if (!active) return;
  const existing = active.querySelector(".error-toast");
  if (existing) existing.remove();
  const toast = document.createElement("div");
  toast.className = "error-toast";
  toast.textContent = msg;
  (active.querySelector("div") || active).prepend(toast);
  setTimeout(() => toast.remove(), 10000);
}

function getDomain(url) {
  try { return new URL(url).hostname.replace("www.", ""); }
  catch { return ""; }
}

function esc(s) {
  if (!s) return "";
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escAttr(s) {
  if (!s) return "";
  return s.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

// ═══════════════════════════════════════════
//  COUNTRY DROPDOWN
// ═══════════════════════════════════════════

const COUNTRIES = [
  "Afghanistan","Albania","Algeria","Argentina","Armenia","Australia","Austria",
  "Azerbaijan","Bangladesh","Belarus","Belgium","Bolivia","Bosnia and Herzegovina",
  "Brazil","Bulgaria","Cambodia","Cameroon","Canada","Chile","China","Colombia",
  "Costa Rica","Croatia","Cuba","Czech Republic","Denmark","Ecuador","Egypt",
  "Ethiopia","Finland","France","Georgia","Germany","Ghana","Greece","Guatemala",
  "Honduras","Hong Kong","Hungary","India","Indonesia","Iran","Iraq","Ireland",
  "Israel","Italy","Jamaica","Japan","Jordan","Kazakhstan","Kenya","Kuwait",
  "Lebanon","Libya","Lithuania","Malaysia","Mexico","Morocco","Mozambique",
  "Myanmar","Nepal","Netherlands","New Zealand","Nicaragua","Nigeria","Norway",
  "Online","Pakistan","Panama","Paraguay","Peru","Philippines","Poland","Portugal",
  "Romania","Russia","Saudi Arabia","Senegal","Serbia","Singapore","Slovakia",
  "South Africa","South Korea","Spain","Sri Lanka","Sudan","Sweden","Switzerland",
  "Syria","Taiwan","Tanzania","Thailand","Tunisia","Turkey","Uganda","Ukraine",
  "United Arab Emirates","United Kingdom","United States","Uruguay","Uzbekistan",
  "Venezuela","Vietnam","Yemen","Zimbabwe"
];

function initCountryDropdown() {
  renderCountryList(COUNTRIES);
}

function renderCountryList(list) {
  const container = document.getElementById("country-list");
  if (!container) return;
  if (list.length === 0) {
    container.innerHTML = '<div class="country-no-results">No results found</div>';
    return;
  }
  const selected = document.getElementById("input-country").value;
  container.innerHTML = list
    .map(c => `<div class="country-option${c === selected ? " selected" : ""}"
         onmousedown="selectCountry('${c}')">${c}</div>`)
    .join("");
}

function filterCountries(query) {
  const filtered = COUNTRIES.filter(c =>
    c.toLowerCase().includes(query.toLowerCase())
  );
  renderCountryList(filtered);
}

function openCountryDropdown() {
  filterCountries(document.getElementById("input-country-search").value);
  document.getElementById("country-list").classList.add("open");
}

function closeCountryDropdown() {
  document.getElementById("country-list").classList.remove("open");
}

function selectCountry(country) {
  document.getElementById("input-country").value = country;
  document.getElementById("input-country-search").value = country;
  closeCountryDropdown();
}

// ═══════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  // Replace these with your actual values from Supabase → Project Settings → API
  const SUPABASE_URL      = "https://gymzfpzinruiupirnmiy.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5bXpmcHppbnJ1aXVwaXJubWl5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNDYzMTcsImV4cCI6MjA4OTgyMjMxN30.Ol2nad3ZaW_RtOXs9RJTf9ameltMTKh93u4zp2MJXR8";

  supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // Restore session if the user was already logged in
  supabaseClient.auth.getSession().then(({ data: { session } }) => {
    if (session) {
      currentUser  = session.user;
      currentToken = session.access_token;
      updateAuthUI(true);
    }
  });

  // Keep token fresh — Supabase silently refreshes JWTs before they expire,
  // this listener catches that and updates currentToken automatically
  supabaseClient.auth.onAuthStateChange((_event, session) => {
    currentUser  = session?.user  ?? null;
    currentToken = session?.access_token ?? null;
    updateAuthUI(!!session);
  });

  showPage("landing");
  document.getElementById("input-topic")?.focus();
  initCountryDropdown();
});
