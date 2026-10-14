// Draws a script: columns (split at the "split here" marks), [Business] filled in,
// objection answers in small boxes underneath, and the reader's text size / look.
const ScriptView = (() => {
  const ALLOWED = new Set(["B", "STRONG", "I", "EM", "U", "H2", "H3", "P", "DIV", "BR", "MARK", "SPAN", "HR", "UL", "OL", "LI"]);
  const KEY = "navigara.scriptView";
  const THEMES = { dark: "Dark", light: "Light", contrast: "High contrast (yellow)" };

  // Keep only simple formatting; drop anything else that was pasted in.
  function clean(html) {
    const t = document.createElement("template");
    t.innerHTML = html || "";
    (function walk(node) {
      for (const el of [...node.childNodes]) {
        if (el.nodeType === 3) continue;
        if (el.nodeType !== 1 || ["SCRIPT", "STYLE"].includes(el.tagName)) { el.remove(); continue; }
        walk(el);
        if (!ALLOWED.has(el.tagName)) { el.replaceWith(...el.childNodes); continue; }
        const bg = el.style.backgroundColor;
        const split = el.tagName === "HR" && el.hasAttribute("data-split");
        [...el.attributes].forEach(a => el.removeAttribute(a.name));
        if (bg && (el.tagName === "SPAN" || el.tagName === "MARK")) el.style.backgroundColor = bg;
        if (split) el.setAttribute("data-split", "");
      }
    })(t.content);
    return t.innerHTML;
  }

  function fill(html, business) {
    const t = document.createElement("template");
    t.innerHTML = html;
    const walker = document.createTreeWalker(t.content, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const n = walker.currentNode;
      if (n.nodeValue.includes("[Business]")) n.nodeValue = n.nodeValue.replaceAll("[Business]", business || "[Business]");
    }
    return t.innerHTML;
  }

  function prefs() {
    try { return { size: 18, theme: "dark", ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
    catch { return { size: 18, theme: "dark" }; }
  }
  function save(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch {} }

  function render(script, objections, business) {
    const p = prefs();
    const body = fill(clean(script ? script.body : ""), business);
    const cols = body.split(/<hr data-split="">/i).map(c => `<div class="sv-col">${c}</div>`).join("");
    const objs = (objections || []).map(o => `
      <div class="sv-obj"><div class="sv-obj-name">${esc(o.name)}</div>${fill(clean(o.body), business)}</div>`).join("");
    return `<div class="script-view theme-${p.theme}" style="font-size:${p.size}px">
      <div class="sv-cols">${script ? cols : '<div class="sv-col muted">No call script in use.</div>'}</div>
      ${objs ? `<div class="sv-objs">${objs}</div>` : ""}</div>`;
  }

  // Text size and look buttons. onChange redraws whatever uses them.
  function controls(onChange) {
    const p = prefs();
    const wrap = document.createElement("div");
    wrap.className = "sv-controls";
    wrap.innerHTML = `<button class="btn small" data-sz="-2" title="Smaller text">A-</button>
      <button class="btn small" data-sz="2" title="Bigger text">A+</button>
      <select class="sv-theme">${Object.entries(THEMES).map(([k, v]) =>
        `<option value="${k}" ${k === p.theme ? "selected" : ""}>${v}</option>`).join("")}</select>`;
    wrap.querySelectorAll("[data-sz]").forEach(b => b.onclick = () => {
      const q = prefs(); q.size = Math.max(12, Math.min(40, q.size + +b.dataset.sz)); save(q); onChange();
    });
    wrap.querySelector("select").onchange = e => { const q = prefs(); q.theme = e.target.value; save(q); onChange(); };
    return wrap;
  }

  return { clean, render, controls };
})();
