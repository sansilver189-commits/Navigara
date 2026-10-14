// Shared by every page: sidebar, practice banner, and small helpers.
const NAV = [
  ["/leads", "Leads"],
  ["/scraper", "Scraper"],
  ["/dialer", "Dialer"],
  ["/analytics", "Analytics"],
  ["/scripts", "Scripts"],
  ["/settings", "Settings"],
];

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== "string" && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, opts);
  if (res.status === 401 && !path.startsWith("/api/login")) {
    location.href = "/login";
    throw new Error("Please log in");
  }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error((data && data.detail) || res.statusText);
  return data;
}

function toast(message, ms = 2200) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Copied " + text); }
  catch { toast("Could not copy"); }
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function renderShell() {
  const side = document.getElementById("sidebar");
  if (!side) return;
  const here = location.pathname;
  side.className = "sidebar";
  side.innerHTML = `
    <div class="brand">Navi<span>gara</span></div>
    <nav class="nav">${NAV.map(([href, label]) =>
      `<a href="${href}" class="${here.startsWith(href) ? "active" : ""}">${label}</a>`).join("")}</nav>
    <div class="sidebar-foot">
      <a class="btn" href="/api/backup">Back up database</a>
      <a class="muted" id="logout" href="/logout" hidden>Log out</a>
    </div>`;
  try {
    const me = await api("/api/me");
    window.ME = me;
    if (me.login_required) document.getElementById("logout").hidden = false;
    if (me.practice) {
      const b = document.createElement("div");
      b.className = "practice-banner";
      b.textContent = "PRACTICE MODE - made-up businesses, calls only pretend to ring. Nothing here is saved.";
      document.body.prepend(b);
    }
  } catch (e) { /* login redirect handled in api() */ }
}

document.addEventListener("DOMContentLoaded", renderShell);
