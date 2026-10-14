// Dialer page. Rules that matter:
//  - The list order is fixed when the page loads; setting a result never moves a row.
//  - Only setting a result moves auto-dial on. A prospect hanging up never starts the next call.
//  - Results are never logged automatically (a voicemail looks exactly like a person answering).
const $ = id => document.getElementById(id);
let S = null;          // page state from the server
let rows = [];         // today's list, in fixed order
let device = null;     // Twilio phone in the browser
let current = null;    // the call in progress
let auto = false;      // auto-dial on?
let timerId = null;
let scriptOn = (() => { try { return localStorage.getItem("navigara.showScript") !== "0"; } catch { return true; } })();

async function init() {
  S = await api("/api/dialer/state");
  S.active = await api("/api/scripts/active");
  rows = S.leads;
  setupCalling();
  renderStats();
  renderRows();
}

// ---------- calling setup ----------

async function setupCalling() {
  if (S.calling === "off") {
    $("notice").innerHTML = `<div class="notice">Calling is not set up yet, so this is a plain list: copy a number,
      call it, then pick the result. See <b>SETUP.md</b> to connect Twilio.</div>`;
    return;
  }
  $("dialControls").hidden = false;
  $("sub").textContent = "Today's calling list. Your numbers: " + S.numbers.join(", ");
  if (S.calling === "practice") return;
  try {
    const { token } = await api("/api/dialer/token");
    device = new Twilio.Device(token, { closeProtection: "A call is in progress. Leave anyway?" });
    device.on("error", e => toast("Phone error: " + (e.message || e), 6000));
    device.on("tokenWillExpire", async () => device.updateToken((await api("/api/dialer/token")).token));
  } catch (e) {
    $("notice").innerHTML = `<div class="notice">Could not connect to Twilio: ${esc(e.message)}. Check the Twilio values in your .env file.</div>`;
    S.calling = "off";
    $("dialControls").hidden = true;
    renderRows();
  }
}

// Practice mode: pretends to ring, and sometimes "answers".
function fakeCall() {
  const handlers = {};
  const call = {
    parameters: { CallSid: "PRACTICE" }, done: false,
    on(ev, fn) { (handlers[ev] = handlers[ev] || []).push(fn); },
    emit(ev) { (handlers[ev] || []).forEach(fn => fn(call)); },
    mute() {},
    disconnect() {
      if (call.done) return;
      call.done = true;
      [call.t1, call.t2, call.t3].forEach(clearTimeout);
      call.emit("disconnect");
    },
  };
  call.t1 = setTimeout(() => call.emit("ringing"), 600);
  if (Math.random() < 0.6) call.t2 = setTimeout(() => { if (!call.done) call.emit("accept"); }, 2500 + Math.random() * 2500);
  else call.t3 = setTimeout(() => call.disconnect(), 30000);  // nobody picks up
  return call;
}

// ---------- calling hours (in the lead's own time zone) ----------

function leadClock(r) {
  if (!r.tz) return null;
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: r.tz, hour: "numeric", minute: "2-digit", hour12: true })
    .formatToParts(new Date());
  const hour24 = +new Intl.DateTimeFormat("en-US", { timeZone: r.tz, hour: "numeric", hourCycle: "h23" }).format(new Date());
  return { text: parts.map(p => p.value).join(""), hour: hour24 };
}
function inHours(r) {
  const c = leadClock(r);
  return !c || (c.hour >= S.call_hours[0] && c.hour < S.call_hours[1]);
}

// ---------- rendering ----------

function renderStats() {
  const s = S.stats, pct = v => v == null ? "-" : v + "%";
  const goalPct = Math.min(100, Math.round(100 * s.dials / (S.goal || 1)));
  $("stats").innerHTML = `
    <div class="stat"><div class="label">Dials</div><div class="value">${s.dials}</div>
      <div class="sub">goal <input class="goal" id="goal" type="number" min="1" value="${S.goal}"></div>
      <div class="goal-bar"><div style="width:${goalPct}%"></div></div></div>
    <div class="stat"><div class="label">Answered</div><div class="value">${s.answered}</div></div>
    <div class="stat"><div class="label">Booked</div><div class="value">${s.booked}</div></div>
    <div class="stat"><div class="label">Answer rate</div><div class="value">${pct(s.answer_rate)}</div></div>
    <div class="stat"><div class="label">Booking rate</div><div class="value">${pct(s.booking_rate)}</div></div>`;
  $("goal").onchange = async e => {
    try { S.goal = (await api("/api/dialer/goal", { method: "POST", body: { goal: +e.target.value } })).goal; renderStats(); }
    catch (err) { toast(err.message); }
  };
}

function renderRows() {
  if (!rows.length) {
    $("rows").innerHTML = `<tr><td colspan="8" class="muted">Nobody to call today. Add leads on the Leads page.</td></tr>`;
    return;
  }
  const canCall = S.calling !== "off";
  const opts = sel => `<option value="">-</option>` + Object.entries(S.results)
    .map(([k, v]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${esc(v)}</option>`).join("");
  $("rows").innerHTML = rows.map((r, i) => {
    const isCurrent = current && current.row.id === r.id;
    const clock = leadClock(r), ok = inHours(r);
    const label = r.kind === "retry" ? '<span class="kind retry">2nd try</span>'
                : r.kind === "callback" ? '<span class="kind retry">call back</span>' : "";
    return `<tr data-id="${r.id}" class="${isCurrent ? "current" : ""} ${r.today_result ? "done" : ""}">
      <td class="sub">${i + 1}</td>
      <td><b>${esc(r.contact || "-")}</b> ${label}<div class="sub">${esc(r.title || "")}</div></td>
      <td>${esc(r.company)}</td>
      <td>${r.pitch ? `<span class="tag ${r.pitch}">${r.pitch}</span>` : ""}</td>
      <td>${r.score ?? ""} ${r.grade ? `<span class="badge ${r.grade}">${r.grade}</span>` : ""}</td>
      <td><button class="linkish copy" data-phone="${esc(r.phone_pretty)}">${esc(r.phone_pretty)}</button>
        ${clock ? `<div class="sub" style="${ok ? "" : "color:var(--warn)"}">${clock.text} their time</div>` : ""}</td>
      <td>${canCall && !current && !r.today_result ? (ok ? `<button class="btn call small" data-call="${r.id}">Call</button>`
          : `<span class="sub" title="Only call ${S.call_hours[0]}:00-${S.call_hours[1]}:00 their time">too late/early</span>`) : ""}</td>
      <td><select class="result-pick" data-result-for="${r.id}">${opts(r.today_result)}</select></td>
    </tr>`;
  }).join("");
}

function fmt(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}

function renderPanel() {
  const p = $("panel");
  if (!current) {
    p.hidden = true;
    $("main").style.paddingBottom = "";
    clearInterval(timerId);
    renderOverlay();
    return;
  }
  const r = current.row;
  const statusText = { connecting: "Connecting...", ringing: "Ringing...", live: "Connected",
                       ended: "Call ended. Pick a result to continue." }[current.status];
  p.hidden = false;
  p.innerHTML = `
    <div class="top">
      <div>
        <div class="who">${esc(r.contact || "")} &middot; ${esc(r.company)}</div>
        <div class="muted">${esc(r.title || "")} ${r.pitch ? `<span class="tag ${r.pitch}">${r.pitch} pitch</span>` : ""}</div>
        <div class="sub">Calling ${esc(r.phone_pretty)} from ${esc(current.from_pretty || "")}</div>
      </div>
      <div>
        <div class="status ${current.status === "live" ? "live" : current.status === "ended" ? "ended" : "ringing"}">${statusText}</div>
        <div class="timer" id="timer">0:00</div>
      </div>
      <div class="controls">
        <button class="btn ${current.muted ? "on" : ""}" id="muteBtn" ${current.status === "ended" ? "disabled" : ""}>${current.muted ? "Unmute" : "Mute"}</button>
        ${S.active.script ? `<button class="btn ${scriptOn ? "on" : ""}" id="scriptBtn">Script ${scriptOn ? "on" : "off"}</button>` : ""}
        ${auto ? `<button class="btn" id="panelPause">Pause after this</button>` : ""}
        <button class="btn hangup" id="hangBtn" ${current.status === "ended" ? "disabled" : ""}>Hang up</button>
      </div>
    </div>
    <div class="sub" style="margin-top:10px">${auto ? "Pick a result to hang up and ring the next lead." : "Pick a result to finish this call."}</div>
    <div class="quick">${Object.entries(S.results).map(([k, v]) =>
      `<button class="btn ${k === "booked" ? "booked" : ""}" data-quick="${k}">${esc(v)}</button>`).join("")}</div>`;
  $("muteBtn").onclick = () => { current.muted = !current.muted; current.call.mute(current.muted); renderPanel(); };
  $("hangBtn").onclick = () => current.call.disconnect();
  if ($("panelPause")) $("panelPause").onclick = pause;
  if ($("scriptBtn")) $("scriptBtn").onclick = toggleScript;
  $("main").style.paddingBottom = (p.offsetHeight + 30) + "px";
  renderOverlay();
  tick();
  clearInterval(timerId);
  timerId = setInterval(tick, 500);
}

// The script covers the lead list while a call is live, and goes away when the call ends.
// It stops at the top edge of the call panel, so it never hides the panel.
function renderOverlay() {
  const o = $("scriptOverlay");
  const show = current && current.status !== "ended" && scriptOn && S.active.script;
  if (!show) { o.hidden = true; return; }
  o.hidden = false;
  o.style.bottom = $("panel").offsetHeight + "px";
  o.innerHTML = `<div class="sv-head"><b>${esc(S.active.script.name)}</b><span id="svc"></span></div>
    ${ScriptView.render(S.active.script, S.active.objections, current.row.company)}`;
  const c = ScriptView.controls(renderOverlay);
  const hide = document.createElement("button");
  hide.className = "btn small"; hide.textContent = "Hide script"; hide.onclick = toggleScript;
  c.append(hide);
  $("svc").append(c);
}

function toggleScript() {
  scriptOn = !scriptOn;
  try { localStorage.setItem("navigara.showScript", scriptOn ? "1" : "0"); } catch {}
  renderPanel();
}

function tick() {
  if (!current || !$("timer")) return;
  const from = current.connectedAt || current.startedAt;
  $("timer").textContent = fmt((current.endedAt || Date.now()) - from);
}

function updateControls() {
  $("startBtn").hidden = auto;
  $("pauseBtn").hidden = !auto;
}

// ---------- calls ----------

async function startCall(row) {
  if (current) return toast("Finish the current call first");
  let t;
  try { t = await api("/api/dialer/ticket", { method: "POST", body: { lead_id: row.id } }); }
  catch (e) { toast(e.message, 5000); auto = false; updateControls(); return; }
  current = { row, from: t.from, from_pretty: t.from_pretty, status: "connecting",
              startedAt: Date.now(), connectedAt: null, endedAt: null, muted: false, sid: null };
  renderRows();
  renderPanel();
  let call;
  try {
    call = S.calling === "practice" ? fakeCall() : await device.connect({ params: { ticket: t.ticket } });
  } catch (e) {
    toast("Could not start the call: " + e.message, 6000);
    current.status = "ended"; current.endedAt = Date.now(); renderPanel();
    return;
  }
  current.call = call;
  const mine = () => current && current.call === call;
  call.on("ringing", () => { if (mine() && current.status === "connecting") { current.status = "ringing"; renderPanel(); } });
  call.on("accept", () => {
    if (!mine()) return;
    current.status = "live"; current.connectedAt = Date.now();
    current.sid = call.parameters && call.parameters.CallSid;
    renderPanel();
  });
  const ended = () => {
    if (!mine() || current.status === "ended") return;
    current.status = "ended"; current.endedAt = Date.now();
    renderPanel();   // waits for you to pick a result; never moves on by itself
  };
  ["disconnect", "cancel", "reject"].forEach(ev => call.on(ev, ended));
  call.on("error", e => { toast("Call error: " + (e.message || e), 6000); ended(); });
}

async function setResult(row, result) {
  const isCurrent = current && current.row.id === row.id;
  const body = { lead_id: row.id, result, replace_event_id: row.event_id };
  if (isCurrent) {
    const end = current.endedAt || Date.now();
    Object.assign(body, {
      from_number: current.from, call_sid: current.sid,
      script_id: S.active.script ? S.active.script.id : null,
      duration_sec: current.connectedAt ? Math.round((end - current.connectedAt) / 1000) : 0,
    });
  }
  let r;
  try { r = await api("/api/dialer/result", { method: "POST", body }); }
  catch (e) { toast("Not saved: " + e.message, 5000); renderRows(); return; }
  row.today_result = result;
  row.event_id = r.event_id;
  S.stats = r.stats;
  renderStats();
  if (isCurrent) {
    const finished = current;
    current = null;
    if (finished.call) finished.call.disconnect();
    renderPanel();
  }
  renderRows();
  if (isCurrent && auto) setTimeout(nextCall, 1200);
}

function nextCall() {
  if (!auto || current) return;
  const next = rows.find(r => !r.today_result && inHours(r));
  if (!next) {
    auto = false; updateControls();
    const waiting = rows.filter(r => !r.today_result).length;
    toast(waiting ? `Stopped: the ${waiting} lead(s) left are outside calling hours in their time zone.`
                  : "That's the end of today's list.", 6000);
    renderRows();
    return;
  }
  startCall(next);
}

function pause() {
  auto = false;
  updateControls();
  if (current) { toast("Paused. Finish this call and dialing stops."); renderPanel(); }
}

// ---------- events ----------

$("startBtn").onclick = () => {
  const left = rows.filter(r => !r.today_result).length;
  if (!left) return toast("Nobody left to call today.");
  if (!confirm(`Start auto-dialing? It will ring ${left} lead(s) one after another. ` +
               `The next call only starts after you pick a result.`)) return;
  auto = true;
  updateControls();
  if (current) renderPanel(); else nextCall();
};
$("pauseBtn").onclick = pause;

document.addEventListener("click", e => {
  const copy = e.target.closest(".copy");
  if (copy) return copyText(copy.dataset.phone);
  const callBtn = e.target.closest("[data-call]");
  if (callBtn) return startCall(rows.find(r => r.id === +callBtn.dataset.call));
  const quick = e.target.closest("[data-quick]");
  if (quick && current) return setResult(current.row, quick.dataset.quick);
});
document.addEventListener("change", e => {
  const sel = e.target.closest("[data-result-for]");
  if (sel && sel.value) setResult(rows.find(r => r.id === +sel.dataset.resultFor), sel.value);
});
window.addEventListener("beforeunload", e => { if (current) { e.preventDefault(); e.returnValue = ""; } });

document.addEventListener("DOMContentLoaded", init);
