/* Jarvis web app: streams the pipeline from /api/ask (server sent events over a POST), types the answer, marks every
   figure with how it was verified, and opens each cited passage in an evidence drawer. No external libraries. */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch { } } };

  const BANKS = { RBC: ["Royal Bank of Canada", "#3b82f6"], TD: ["Toronto-Dominion Bank", "#22c55e"], BMO: ["Bank of Montreal", "#06b6d4"],
                  BNS: ["Scotiabank", "#f43f5e"], CIBC: ["CIBC", "#a855f7"], NWT: ["Northwind Trust", "#94a3b8"], HBL: ["Harbourline Bank", "#94a3b8"] };
  const I = {
    scope: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/></svg>',
    rewrite: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
    retrieve: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg>',
    answer: '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h7"/></svg>',
    verify: '<svg viewBox="0 0 24 24"><path d="M5 12l5 5 9-10"/></svg>',
    search_filings: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg>',
    get_filing_list: '<svg viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>',
    compare_sections: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="7" height="16" rx="2"/><rect x="14" y="4" width="7" height="16" rx="2"/></svg>',
    extract_metrics: '<svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    risk_language_diff: '<svg viewBox="0 0 24 24"><path d="M5 7h8M5 12h14M5 17h6M17 5v4M15 7h4"/></svg>',
    survey_banks: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
    calculate: '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="14" height="18" rx="3"/><path d="M8 7h8M8 12h2M14 12h2M8 16h2M14 16h2"/></svg>',
    think: '<svg viewBox="0 0 24 24"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/></svg>',
    copy: '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg>',
    warn: '<svg viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  };
  const EXAMPLES = [
    { tag: "Quarterly", mode: "answer", q: "What was BMO's net income in Q2 2025 compared with Q1 2025?" },
    { tag: "Capital", mode: "answer", q: "What was RBC's CET1 ratio at the end of fiscal 2025?" },
    { tag: "Market risk", mode: "answer", q: "What was CIBC's average total VaR for fiscal 2025?" },
    { tag: "Quarter end date", mode: "answer", q: "What was Scotiabank's CET1 capital ratio as at April 30, 2025?" },
    { tag: "Research", mode: "research", q: "Compare the CET1 ratios of RBC and TD at the end of fiscal 2025." },
    { tag: "Research", mode: "research", q: "By what percentage did BMO's net income change from fiscal 2024 to fiscal 2025?" },
  ];
  const STAGES = [["scope", "Scope"], ["rewrite", "Rewrite"], ["retrieve", "Retrieve"], ["answer", "Answer"], ["verify", "Verify"]];

  const state = { role: store.get("jarvis.role") || "analyst", mode: "answer", history: [], busy: false };
  const thread = $("#thread"), q = $("#q"), send = $("#send");

  /* ---------- small helpers ---------- */
  const toast = msg => { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("on"), 1800); };
  const scrollDown = () => thread.scrollTo({ top: thread.scrollHeight, behavior: reduced ? "auto" : "smooth" });
  const fmt = n => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n);
  function countUp(node, to, f = x => Math.round(x).toLocaleString()) {
    if (reduced) { node.textContent = f(to); return; }
    const t0 = performance.now(), d = 1200;
    const tick = t => { const p = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - p, 3); node.textContent = f(to * e); if (p < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  function setStatus(text, err) { $("#statusText").textContent = text; $("#status").classList.toggle("err", !!err); }
  function setBusy(b) { state.busy = b; document.body.classList.toggle("busy", b); send.disabled = b; setStatus(b ? "Working" : "Ready"); }
  function seg(root, value, onPick) {
    const btns = [...root.querySelectorAll("button")];
    const pick = v => { btns.forEach(b => b.classList.toggle("on", b.dataset.v === v)); onPick(v); };
    btns.forEach(b => b.addEventListener("click", () => pick(b.dataset.v)));
    pick(value);
    return pick;
  }

  /* ---------- a small, safe markdown renderer (the text is escaped first) ---------- */
  function inline(s) {
    return s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<i>$2</i>");
  }
  function markdown(src) {
    const lines = esc(src).replace(/\r/g, "").split("\n");
    let html = "", list = null, para = [];
    const flushP = () => { if (para.length) { html += "<p>" + inline(para.join("<br>")) + "</p>"; para = []; } };
    const flushL = () => { if (list) { html += `</${list}>`; list = null; } };
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
        flushP(); flushL();
        const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
        html += "<table><tr>" + cells(line).map(c => `<th>${c}</th>`).join("") + "</tr>";
        i += 2;
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { html += "<tr>" + cells(lines[i]).map(c => `<td>${c}</td>`).join("") + "</tr>"; i++; }
        html += "</table>"; i--; continue;
      }
      let m;
      if ((m = line.match(/^#{1,4}\s+(.*)/))) { flushP(); flushL(); html += `<h4>${inline(m[1])}</h4>`; continue; }
      if ((m = line.match(/^\s*[-*•]\s+(.*)/))) { flushP(); if (list !== "ul") { flushL(); html += "<ul>"; list = "ul"; } html += `<li>${inline(m[1])}</li>`; continue; }
      if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { flushP(); if (list !== "ol") { flushL(); html += "<ol>"; list = "ol"; } html += `<li>${inline(m[1])}</li>`; continue; }
      if (!line.trim()) { flushP(); flushL(); continue; }
      flushL(); para.push(line);
    }
    flushP(); flushL();
    return html;
  }

  /* ---------- figures and citations: walk the rendered text and wrap what was checked ---------- */
  function decorate(root, checks, cites) {
    const figs = (checks || []).map(c => ({ text: c.figure.trim(), cls: c.supported ? (c.computed ? "calc" : "ok") : "warn",
      tip: c.supported ? (c.computed ? "Computed: " + c.computed : "Found in the cited passage") : (c.period ? "Not verified: " + c.period : "Not found in the cited passages") }))
      .filter(f => f.text.length > 1).sort((a, b) => b.text.length - a.text.length);
    const citeRe = /\[((?:T\d+:)?S\d+(?:\s*,\s*(?:T\d+:)?S\d+)*)\]/g;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      let text = node.nodeValue, parts = [{ t: text }];
      for (const f of figs) {
        parts = parts.flatMap(p => {
          if (p.el || !p.t.includes(f.text)) return [p];
          const out = []; p.t.split(f.text).forEach((s, i, a) => { if (s) out.push({ t: s }); if (i < a.length - 1) out.push({ el: "fig", f }); });
          return out;
        });
      }
      parts = parts.flatMap(p => {
        if (p.el) return [p];
        const out = []; let last = 0, m; citeRe.lastIndex = 0;
        while ((m = citeRe.exec(p.t))) {
          if (m.index > last) out.push({ t: p.t.slice(last, m.index) });
          m[1].split(/\s*,\s*/).forEach(id => out.push({ el: "cite", id }));
          last = m.index + m[0].length;
        }
        if (last < p.t.length) out.push({ t: p.t.slice(last) });
        return out;
      });
      if (parts.length === 1 && !parts[0].el) continue;
      const frag = document.createDocumentFragment();
      for (const p of parts) {
        if (!p.el) frag.append(p.t);
        else if (p.el === "fig") { const s = el("span", "fig " + p.f.cls); s.textContent = p.f.text; s.dataset.tip = p.f.tip; frag.append(s); }
        else {
          const b = el("button", "cite"); b.textContent = p.id.replace(":", "·"); b.title = "Open passage " + p.id;
          b.addEventListener("click", () => cites[p.id] ? openDrawer(cites[p.id], checks) : toast("That passage is not in the cited set"));
          frag.append(b);
        }
      }
      node.replaceWith(frag);
    }
  }

  /* ---------- evidence drawer ---------- */
  function openDrawer(src, checks) {
    const [name, color] = BANKS[src.bank] || [src.bank, "#94a3b8"];
    $("#dKicker").textContent = "Evidence " + (src.id || "");
    $("#dTitle").innerHTML = `<span style="color:${color}">●</span> ${esc(name)}`;
    $("#dMeta").innerHTML = [src.document, src.period, src.section, src.page ? "page " + src.page : ""].filter(Boolean).map(x => `<span>${esc(x)}</span>`).join("");
    let body = esc(src.text || "No passage text was returned.");
    (checks || []).filter(c => c.supported).forEach(c => {
      const raw = c.figure.replace(/^\$/, "").replace(/\s*(million|billion|bps|basis points)$/i, "").trim();
      if (raw.length > 1) body = body.split(esc(raw)).join(`<mark>${esc(raw)}</mark>`);
    });
    $("#dBody").innerHTML = body;
    const link = $("#dLink");
    if (src.url) { link.href = src.url; link.hidden = false; } else link.hidden = true;
    $("#drawer").classList.add("open"); $("#drawer").setAttribute("aria-hidden", "false"); $("#scrim").classList.add("on");
    const first = $("#dBody mark"); if (first) setTimeout(() => first.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" }), 350);
  }
  function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true"); $("#scrim").classList.remove("on"); $("#side").classList.remove("open"); }

  /* ---------- one exchange ---------- */
  function userBubble(text) {
    const m = el("div", "msg user"); const b = el("div", "bubble"); b.textContent = text; m.append(b); thread.append(m);
  }
  function botShell(mode) {
    const m = el("div", "msg");
    const who = el("div", "who", '<div class="orb small"><i></i><i></i><i></i></div>');
    const bot = el("div", "bot"); const card = el("div", "botcard"); bot.append(card); m.append(who, bot); thread.append(m);
    const ui = { card, mode, t0: performance.now() };
    if (mode === "answer") {
      const pipe = el("div", "pipe");
      ui.stages = {};
      STAGES.forEach(([k, label]) => {
        const s = el("div", "stage", `<div class="node">${I[k]}</div><div class="lbl">${label}</div><div class="det"></div>`);
        pipe.append(s); ui.stages[k] = s;
      });
      card.append(pipe);
      activate(ui, "scope");
    } else {
      ui.trail = el("div", "trail"); card.append(ui.trail);
    }
    ui.head = el("div", "head"); ui.answer = el("div", "answer"); card.append(ui.head, ui.answer);
    return ui;
  }
  function activate(ui, key, detail) {
    if (!ui.stages) return;
    const order = STAGES.map(s => s[0]); const at = order.indexOf(key);
    order.forEach((k, i) => {
      const s = ui.stages[k];
      if (i < at) { s.classList.remove("active"); s.classList.add("done"); }
      if (i === at) { s.classList.add("active"); }
    });
    if (detail != null && ui.stages[key]) ui.stages[key].querySelector(".det").textContent = detail;
  }
  function complete(ui, key, detail) {
    if (!ui.stages || !ui.stages[key]) return;
    const s = ui.stages[key]; s.classList.remove("active"); s.classList.add("done");
    if (detail != null) s.querySelector(".det").textContent = detail;
    const order = STAGES.map(x => x[0]); const next = order[order.indexOf(key) + 1];
    if (next) activate(ui, next);
  }
  function onStep(ui, ev) {
    if (ui.mode === "answer") {
      if (ev.name === "scope") {
        const bits = [...(ev.banks || []), ...(ev.years || []).map(String), ...(ev.quarters || []).map(x => x === "annual" ? "annual" : x)];
        complete(ui, "scope", bits.length ? bits.join(" · ") : "all filings");
        ui.scope = ev;
      } else if (ev.name === "rewrite") complete(ui, "rewrite", "HyDE query");
      else if (ev.name === "retrieve") {
        const n = (ev.passages || []).length, nb = (ev.passages || []).filter(p => p.neighbour).length;
        complete(ui, "retrieve", n + " passages" + (nb ? ` (+${nb} context)` : ""));
      } else if (ev.name === "retry") { activate(ui, "retrieve", "retrying wider"); }
      else if (ev.name === "answer") complete(ui, "answer", (ev.model || "").split(".").pop().split(":")[0].replace("anthropic.", ""));
      else if (ev.name === "verify") complete(ui, "verify", `${ev.verified}/${ev.figures} figures`);
    } else {
      if (ev.name === "think") {
        if (ui.thinking) ui.thinking.remove();
        ui.thinking = el("div", "tstep thinking", `<div class="ti">${I.think}</div><span class="shimmer">Planning step ${ev.step}</span>`);
        ui.trail.append(ui.thinking);
      } else if (ev.name === "tool") {
        if (ui.thinking) { ui.thinking.remove(); ui.thinking = null; }
        const args = Object.entries(ev.args || {}).map(([k, v]) => Array.isArray(v) ? v.join(", ") : v).join(" · ");
        const res = ev.tool === "calculate" ? (ev.result != null ? "= " + ev.result : "") : `${ev.results} passages`;
        ui.trail.append(el("div", "tstep", `<div class="ti">${I[ev.tool] || I.retrieve}</div><span class="tn">${esc(ev.tool)}</span><span class="ta">${esc(args)}</span><span class="tr">${esc(res)}</span>`));
      } else if (ev.name === "verify") { if (ui.thinking) { ui.thinking.remove(); ui.thinking = null; } }
    }
    scrollDown();
  }

  function confidenceRing(level) {
    const pct = { high: 1, medium: .62, low: .3 }[level] ?? .3, c = 2 * Math.PI * 7;
    const w = el("span", "conf " + (level || "low"), `<svg viewBox="0 0 18 18"><circle class="track" cx="9" cy="9" r="7"/><circle class="val" cx="9" cy="9" r="7" stroke-dasharray="${c}" stroke-dashoffset="${c}"/></svg>${esc(level || "low")} confidence`);
    requestAnimationFrame(() => requestAnimationFrame(() => { w.querySelector(".val").style.strokeDashoffset = String(c * (1 - pct)); }));
    return w;
  }

  function typeOut(node, text) {
    return new Promise(res => {
      if (reduced || text.length > 2400) { node.textContent = text; return res(); }
      node.classList.add("typing"); node.textContent = "";
      const words = text.split(/(\s+)/); let i = 0;
      const step = () => {
        const n = Math.max(1, Math.round(words.length / 90));
        node.textContent += words.slice(i, i + n).join(""); i += n;
        if (i % 12 === 0) scrollDown();
        if (i < words.length) setTimeout(step, 16); else { node.classList.remove("typing"); res(); }
      };
      step();
    });
  }

  async function render(ui, out) {
    const ans = out.answer || "";
    if (ui.mode === "answer") {
      ui.head.append(confidenceRing(out.confidence));
      const sc = out.scope || ui.scope || {};
      const tags = [...(sc.banks || []), ...(sc.years || []).map(y => "FY" + y), ...(sc.quarters || []).filter(x => x !== "annual")];
      if (tags.length) ui.head.append(el("span", "scope", tags.map(t => `<span>${esc(t)}</span>`).join("")));
    } else {
      ui.head.append(el("span", "conf medium", `<svg viewBox="0 0 18 18"><circle class="val" cx="9" cy="9" r="7" style="stroke:var(--calc)"/></svg>${out.iterations || 0} steps · ${(out.tool_calls || []).length} tool calls`));
    }
    await typeOut(ui.answer, ans);
    const rich = el("div", "answer rich", markdown(ans));
    const cites = {};
    (out.sources || []).forEach(s => { if (s && s.id) cites[s.id] = s; });
    (out.passages || []).forEach(p => { cites[p.id] = p; });
    decorate(rich, out.figure_check, cites);
    ui.answer.replaceWith(rich); ui.answer = rich;

    const checks = out.figure_check || [];
    if (checks.length) {
      const ok = checks.filter(c => c.supported && !c.computed).length, calc = checks.filter(c => c.computed).length, bad = checks.filter(c => !c.supported).length;
      ui.card.append(el("div", "legend",
        `<span><i style="background:var(--ok)"></i>${ok} found in source</span>` + (calc ? `<span><i style="background:var(--calc)"></i>${calc} recomputed</span>` : "") +
        (bad ? `<span><i style="background:var(--warn)"></i>${bad} not verified</span>` : "")));
    }
    (out.caveats || []).forEach(c => ui.card.append(el("div", "caveat", I.warn + `<span>${esc(c)}</span>`)));
    const srcs = [...(out.sources || []), ...(out.passages || [])].filter(s => s && typeof s === "object" && s.id);
    const seen = new Set();
    const uniq = srcs.filter(s => { const k = s.id; if (seen.has(k)) return false; seen.add(k); return true; });
    if (uniq.length) {
      const row = el("div", "sources");
      uniq.forEach((s, i) => {
        const [name, color] = BANKS[s.bank] || [s.bank, "#94a3b8"];
        const b = el("button", "src", `<div class="sid">${esc(s.id)}</div><div class="sb"><i style="background:${color}"></i>${esc(name)}</div><div class="sd">${esc(s.document)} · ${esc(s.period || "")}</div><div class="sd">${esc(s.section || "")}${s.page ? " · p." + esc(s.page) : ""}</div>`);
        b.style.animationDelay = (i * 60) + "ms";
        b.addEventListener("click", () => openDrawer(s, out.figure_check));
        row.append(b);
      });
      ui.card.append(row);
    }
    const meta = el("div", "meta");
    const secs = ((performance.now() - ui.t0) / 1000).toFixed(1);             // what the analyst waited, end to end
    meta.innerHTML = `<span title="Total time">${I.clock} ${esc(secs)} s</span><span title="Model cost">$${Number(out.usd || 0).toFixed(4)}</span>` +
      (out.retried ? "<span>retried wider</span>" : "");
    const copy = el("button", "", I.copy + " Copy");
    copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(ans); toast("Answer copied"); } catch { toast("Copy is not available here"); } });
    meta.append(copy);
    ui.card.append(meta);
    scrollDown();
  }

  async function ask(text) {
    text = text.trim();
    if (!text || state.busy) return;
    $("#hero")?.remove();
    if (!state.history.length) $("#title").textContent = text.length > 70 ? text.slice(0, 68) + "…" : text;
    const li = el("li"); li.textContent = text; $("#history").append(li);
    userBubble(text); q.value = ""; grow(); setBusy(true);
    const ui = botShell(state.mode); scrollDown();
    li.addEventListener("click", () => ui.card.scrollIntoView({ behavior: "smooth", block: "start" }));
    try {
      const resp = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, mode: state.mode, role: state.role, history: state.history }) });
      if (!resp.ok || !resp.body) throw new Error("The server answered " + resp.status);
      const reader = resp.body.getReader(), dec = new TextDecoder(); let buf = "", result = null, error = null;
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let cut;
        while ((cut = buf.indexOf("\n\n")) >= 0) {
          const block = buf.slice(0, cut); buf = buf.slice(cut + 2);
          const ev = (block.match(/^event: (.*)$/m) || [])[1], data = (block.match(/^data: (.*)$/m) || [])[1];
          if (!ev || !data) continue;
          const obj = JSON.parse(data);
          if (ev === "step") onStep(ui, obj); else if (ev === "result") result = obj; else if (ev === "error") error = obj.message;
        }
      }
      if (error) throw new Error(error);
      if (!result) throw new Error("No answer came back.");
      await render(ui, result);
      state.history.push({ role: "user", content: text }, { role: "assistant", content: result.answer || "" });
    } catch (e) {
      ui.card.classList.add("error");
      Object.values(ui.stages || {}).forEach(s => s.classList.remove("active"));
      ui.answer.textContent = e.message || String(e);
      setStatus("Error", true);
    } finally {
      setBusy(false);
      if ($("#status").classList.contains("err")) setStatus("Error", true);
      q.focus();
    }
  }

  /* ---------- composer ---------- */
  function grow() { q.style.height = "auto"; q.style.height = Math.min(200, q.scrollHeight) + "px"; }
  q.addEventListener("input", grow);
  q.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(q.value); } });
  send.addEventListener("click", () => ask(q.value));
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); q.focus(); }
    if (e.key === "Escape") closeDrawer();
  });

  /* ---------- sidebar, theme, mode, role ---------- */
  const pickMode = seg($("#mode"), state.mode, v => { state.mode = v; q.placeholder = v === "research" ? "Ask a research question across banks or years" : "Ask about a bank, a risk and a period"; });
  seg($("#role"), state.role, v => {
    state.role = v; store.set("jarvis.role", v);
    $("#roleNote").textContent = v === "analyst" ? "Public filings only." : "Public filings and internal memos.";
  });
  $("#newChat").addEventListener("click", () => location.reload());
  $("#menu").addEventListener("click", () => { $("#side").classList.add("open"); $("#scrim").classList.add("on"); });
  $("#scrim").addEventListener("click", closeDrawer);
  $("#dClose").addEventListener("click", closeDrawer);
  const theme = store.get("jarvis.theme"); if (theme) document.documentElement.dataset.theme = theme;
  $("#theme").addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = t; store.set("jarvis.theme", t);
  });

  /* ---------- the empty state ---------- */
  EXAMPLES.forEach((ex, i) => {
    const c = el("button", "card", `<div class="tag ${ex.mode === "research" ? "research" : ""}">${ex.mode === "research" ? I.think : I.retrieve} ${esc(ex.tag)}</div><div class="q">${esc(ex.q)}</div>`);
    c.style.animationDelay = (120 + i * 70) + "ms";
    c.addEventListener("pointermove", e => { const r = c.getBoundingClientRect(); c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px"); });
    c.addEventListener("click", () => { pickMode(ex.mode); ask(ex.q); });
    $("#cards").append(c);
  });
  const orb = $("#heroOrb");
  if (orb && !reduced) addEventListener("pointermove", e => {
    const dx = (e.clientX / innerWidth - .5) * 18, dy = (e.clientY / innerHeight - .5) * 18;
    orb.style.transform = `translate(${dx}px, ${dy}px)`;
  });

  fetch("/api/meta").then(r => r.json()).then(m => {
    countUp($("#sFilings"), m.filings); countUp($("#sChunks"), m.chunks, x => fmt(Math.round(x))); countUp($("#sTokens"), m.tokens, x => fmt(Math.round(x)));
    $("#banks").innerHTML = (m.banks || []).filter(b => BANKS[b] && !["NWT", "HBL"].includes(b)).map(b => `<span class="bank"><i style="background:${BANKS[b][1]}"></i>${b}</span>`).join("");
    if (m.models?.error) { $("#models").innerHTML = `<span style="color:var(--bad)">${esc(m.models.error)}</span>`; setStatus("Sign in needed", true); }
    else $("#models").innerHTML = `<div>Answers <b>${esc(m.models.answers)}</b></div><div>Judge <b>${esc(m.models.judge)}</b></div><div>Provider <b>${esc(m.models.provider)}</b></div>`;
  }).catch(() => setStatus("Server unreachable", true));

  /* ---------- starfield: slow drift, gentle twinkle ---------- */
  const cv = $("#stars"), cx = cv.getContext("2d");
  let stars = [];
  function size() {
    cv.width = innerWidth * devicePixelRatio; cv.height = innerHeight * devicePixelRatio;
    stars = Array.from({ length: Math.round(innerWidth * innerHeight / 9000) }, () => ({
      x: Math.random() * cv.width, y: Math.random() * cv.height, r: (Math.random() * 1.2 + .3) * devicePixelRatio,
      s: Math.random() * .15 + .03, p: Math.random() * Math.PI * 2 }));
  }
  size(); addEventListener("resize", size);
  function frame(t) {
    cx.clearRect(0, 0, cv.width, cv.height);
    const fast = document.body.classList.contains("busy") ? 4 : 1;
    for (const s of stars) {
      s.y -= s.s * fast; if (s.y < 0) { s.y = cv.height; s.x = Math.random() * cv.width; }
      const a = .25 + .35 * (1 + Math.sin(t / 900 + s.p)) / 2;
      cx.fillStyle = `rgba(200,215,255,${a})`; cx.beginPath(); cx.arc(s.x, s.y, s.r, 0, 7); cx.fill();
    }
    if (!reduced) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  q.focus();
})();
