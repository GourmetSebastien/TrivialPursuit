import { store, PLAYER_PALETTE } from "./store.js";
import { GameEngine, State, newPlayer } from "./engine.js";
import { Sound } from "./sound.js";
import { Wheel } from "./wheel.js";
import * as xl from "./excel.js";
import { textOn } from "./util.js";

const root = document.getElementById("app");
const sound = new Sound(store);
const MIN_PLAYERS = 2;
const MAX_PLAYERS = 8;
const REQUIRED_THEMES = 5;

let cleanup = null;
let deferredInstall = null;

// ---------------------------------------------------------------------------
// Small DOM helpers
// ---------------------------------------------------------------------------

function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
}

function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "html") el.innerHTML = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  append(el, kids);
  return el;
}

function show(node, onLeave) {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  cleanup = onLeave || null;
  root.replaceChildren(node);
  window.scrollTo(0, 0);
}

function toast(message) {
  document.querySelectorAll(".toast").forEach((old) => old.remove());
  const t = h("div", { class: "toast", role: "status" }, message);
  document.body.append(t);
  requestAnimationFrame(() => t.classList.add("show"));
  setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => t.remove(), 300);
  }, 2800);
}

/** Modal dialog. Resolves with the id of the clicked action, or null if dismissed. */
function modal({ title, body, actions }) {
  return new Promise((resolve) => {
    const dlg = h("dialog", { class: "modal" });
    const bar = h(
      "div",
      { class: "modal-actions" },
      actions.map((a) =>
        h(
          "button",
          {
            type: "button",
            class: "btn " + (a.class || ""),
            onclick: () => {
              if (a.validate && !a.validate()) return;
              dlg.close(a.id);
            },
          },
          a.label
        )
      )
    );
    dlg.append(h("h2", {}, title));
    if (body) dlg.append(body);
    dlg.append(bar);
    dlg.addEventListener("close", () => {
      const value = dlg.returnValue || null;
      dlg.remove();
      resolve(value);
    });
    document.body.append(dlg);
    dlg.showModal();
  });
}

async function confirmBox(message, { ok = "Confirmer", danger = false } = {}) {
  const res = await modal({
    title: "Confirmation",
    body: h("p", {}, message),
    actions: [
      { id: "cancel", label: "Annuler" },
      { id: "ok", label: ok, class: danger ? "danger" : "primary" },
    ],
  });
  return res === "ok";
}

async function promptBox(title, label, value = "") {
  const input = h("input", { type: "text", value, class: "field", autocomplete: "off" });
  const res = await modal({
    title,
    body: h("label", { class: "stack" }, label, input),
    actions: [
      { id: "cancel", label: "Annuler" },
      { id: "ok", label: "OK", class: "primary", validate: () => input.value.trim() !== "" },
    ],
  });
  return res === "ok" ? input.value.trim() : null;
}

function safeColor(c) {
  return /^#[0-9a-f]{6}$/i.test(c) ? c : "#888888";
}

function diskSVG(themes, wedges, awaitingFinal, size = 46) {
  const c = size / 2;
  const r = size / 2 - 4;
  const n = themes.length;
  let paths = "";
  themes.forEach((t, i) => {
    const a0 = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    const a1 = a0 + (2 * Math.PI) / n;
    const x0 = c + r * Math.cos(a0);
    const y0 = c + r * Math.sin(a0);
    const x1 = c + r * Math.cos(a1);
    const y1 = c + r * Math.sin(a1);
    const fill = wedges.has(t.id) ? safeColor(t.color) : "#3a3a3a";
    paths += `<path d="M${c},${c} L${x0},${y0} A${r},${r} 0 0 1 ${x1},${y1} Z" fill="${fill}" stroke="#111" stroke-width="1.2"/>`;
  });
  const ring = awaitingFinal
    ? `<circle cx="${c}" cy="${c}" r="${r + 2}" fill="none" stroke="#f1c40f" stroke-width="3"/>`
    : "";
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" aria-hidden="true">${paths}${ring}</svg>`;
}

function applyTheme() {
  const theme = store.getSetting("ui_theme");
  document.documentElement.dataset.theme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#1e1f26" : "#f5f6fa");
}

// ---------------------------------------------------------------------------
// Main menu
// ---------------------------------------------------------------------------

function showMenu() {
  const hasSave = !!store.loadGame();
  const themeCount = store.listThemes().length;
  const node = h(
    "section",
    { class: "screen menu" },
    h("div", { class: "logo", "aria-hidden": "true" }, "🎡"),
    h("h1", {}, "Trivial Pursuit"),
    h("p", { class: "sub" }, "Entre Potes — le quiz maison"),
    hasSave && h("button", { class: "btn primary big", onclick: resumeGame }, "Reprendre la partie"),
    h("button", { class: "btn big", onclick: newGame }, "Nouvelle partie"),
    h("button", { class: "btn big", onclick: () => showQuestions() }, "Questions"),
    h("button", { class: "btn big", onclick: showSettings }, "Paramètres"),
    deferredInstall && h("button", { class: "btn ghost", onclick: installApp }, "📲 Installer l'application"),
    h(
      "p",
      { class: "hint" },
      themeCount
        ? `${themeCount} thème(s) · ${store.totalQuestions()} question(s)`
        : "Aucune question pour l'instant : va dans « Questions » pour importer ton fichier Excel."
    )
  );
  show(node);
}

async function installApp() {
  if (!deferredInstall) return;
  deferredInstall.prompt();
  await deferredInstall.userChoice;
  deferredInstall = null;
  showMenu();
}

async function newGame() {
  sound.play("click");
  if (store.loadGame()) {
    const ok = await confirmBox("Une partie sauvegardée existe. La nouvelle partie l'écrasera. Continuer ?", {
      ok: "Continuer",
    });
    if (!ok) return;
  }
  showWizard();
}

function resumeGame() {
  sound.play("click");
  const saved = store.loadGame();
  try {
    const themes = saved.theme_ids.map((id) => {
      const t = store.getTheme(id);
      if (!t || !store.countQuestions(id)) throw new Error("missing");
      return t;
    });
    showGame(null, themes, saved);
  } catch (e) {
    store.clearGame();
    toast("La partie sauvegardée n'est plus valide (thèmes ou questions supprimés).");
    showMenu();
  }
}

// ---------------------------------------------------------------------------
// New game wizard
// ---------------------------------------------------------------------------

function showWizard() {
  let step = 0;
  const names = ["", ""];
  const selected = new Set();
  const node = h("section", { class: "screen" });

  const nameOf = (i) => names[i].trim() || `Joueur ${i + 1}`;

  function stepPlayers() {
    const list = h("div", { class: "stack" });
    names.forEach((value, i) => {
      list.append(
        h(
          "label",
          { class: "stack" },
          `Joueur ${i + 1}`,
          h("input", {
            type: "text",
            class: "field",
            value,
            placeholder: `Joueur ${i + 1}`,
            autocomplete: "off",
            oninput: (e) => (names[i] = e.target.value),
          })
        )
      );
    });
    const setCount = (n) => {
      n = Math.max(MIN_PLAYERS, Math.min(MAX_PLAYERS, n));
      while (names.length < n) names.push("");
      names.length = n;
      render();
    };
    return h(
      "div",
      {},
      h("h2", {}, "Combien de joueurs ?"),
      h(
        "div",
        { class: "stepper" },
        h("button", { class: "btn round", "aria-label": "Moins", onclick: () => setCount(names.length - 1) }, "−"),
        h("span", { class: "count" }, names.length),
        h("button", { class: "btn round", "aria-label": "Plus", onclick: () => setCount(names.length + 1) }, "+")
      ),
      list
    );
  }

  function stepThemes() {
    const themes = store.listThemes();
    const status = h("p", { class: "hint" });
    const updateStatus = () => {
      const low = themes.filter((t) => selected.has(t.id) && store.countQuestions(t.id) <= 2).map((t) => t.name);
      status.textContent =
        `${selected.size} / ${REQUIRED_THEMES} thème(s) sélectionné(s).` +
        (low.length ? `  ⚠️ Peu de questions pour : ${low.join(", ")}` : "");
    };
    const list = h("div", { class: "stack" });
    if (!themes.length) list.append(h("p", { class: "hint" }, "Aucun thème. Importe d'abord des questions."));
    themes.forEach((t) => {
      const count = store.countQuestions(t.id);
      const row = h(
        "button",
        {
          type: "button",
          class: "theme-pick" + (selected.has(t.id) ? " on" : ""),
          disabled: count === 0,
          onclick: () => {
            if (selected.has(t.id)) selected.delete(t.id);
            else if (selected.size >= REQUIRED_THEMES) return toast(`Maximum ${REQUIRED_THEMES} thèmes.`);
            else selected.add(t.id);
            row.classList.toggle("on", selected.has(t.id));
            updateStatus();
          },
        },
        h("span", { class: "dot", style: { background: safeColor(t.color) } }),
        h("span", { class: "grow" }, t.name),
        h("span", { class: "muted" }, `${count} q.`)
      );
      list.append(row);
    });
    updateStatus();
    return h("div", {}, h("h2", {}, `Choisis ${REQUIRED_THEMES} thèmes`), list, status);
  }

  function next() {
    sound.play("click");
    if (step === 0) {
      const all = names.map((_, i) => nameOf(i).toLowerCase());
      if (new Set(all).size !== all.length) return toast("Les noms des joueurs doivent être différents.");
      step = 1;
      return render();
    }
    if (selected.size !== REQUIRED_THEMES) return toast(`Sélectionne exactement ${REQUIRED_THEMES} thèmes.`);
    const themes = store.listThemes().filter((t) => selected.has(t.id));
    if (themes.some((t) => store.countQuestions(t.id) === 0)) return toast("Un thème n'a aucune question.");
    const players = names.map((_, i) => newPlayer(nameOf(i), PLAYER_PALETTE[i % PLAYER_PALETTE.length]));
    showGame(players, themes, null);
  }

  function render() {
    node.replaceChildren(
      h("header", { class: "bar" }, h("h1", {}, "Nouvelle partie")),
      step === 0 ? stepPlayers() : stepThemes(),
      h(
        "footer",
        { class: "actions" },
        h(
          "button",
          {
            class: "btn",
            onclick: () => {
              sound.play("click");
              if (step === 0) showMenu();
              else {
                step = 0;
                render();
              }
            },
          },
          step === 0 ? "Menu" : "Précédent"
        ),
        h("button", { class: "btn primary", onclick: next }, step === 0 ? "Suivant" : "Démarrer la partie")
      )
    );
  }

  render();
  show(node);
}

// ---------------------------------------------------------------------------
// Game
// ---------------------------------------------------------------------------

function showGame(players, themes, saved) {
  const questionsByTheme = {};
  themes.forEach((t) => (questionsByTheme[t.id] = store.listQuestions(t.id)));
  const avoidRepeats = store.getSetting("avoid_repeats");
  const engine = saved
    ? GameEngine.restore(saved, themes, questionsByTheme, avoidRepeats)
    : new GameEngine(players, themes, questionsByTheme, avoidRepeats);

  let busy = false;
  let destroyed = false;
  const timers = new Set();
  const later = (fn, ms) => {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
  };

  // --- layout ---
  const lblTurn = h("div", { class: "turn" });
  const playersBar = h("div", { class: "players" });
  const lblInstruction = h("p", { class: "instruction" });

  const canvas = h("canvas", { class: "wheel", "aria-label": "Roue des thèmes. Touche pour la lancer." });
  const wheel = new Wheel(canvas, themes);
  wheel.onTap = primary;
  const panelWheel = h("div", { class: "panel center" }, canvas);

  const qTheme = h("div", { class: "q-theme" });
  const qText = h("div", { class: "q-text" });
  const aText = h("div", { class: "a-text" });
  const btnReveal = h("button", { class: "btn primary big", onclick: reveal }, "Révéler la réponse");
  const btnOk = h("button", { class: "btn success big", onclick: () => answer(true) }, "✅ Bonne réponse");
  const btnKo = h("button", { class: "btn danger big", onclick: () => answer(false) }, "❌ Mauvaise réponse");
  const panelQuestion = h(
    "div",
    { class: "panel" },
    qTheme,
    h("div", { class: "q-card", onclick: () => engine.state === State.QUESTION && reveal() }, qText, aText),
    h("div", { class: "stack" }, btnReveal, btnOk, btnKo)
  );

  const panelShot = h(
    "div",
    { class: "panel center" },
    h("p", { class: "shot-label" }, "Mauvaise réponse… cul sec ! 🥃"),
    h("div", {
      class: "glass-wrap",
      html: `<svg class="glass" viewBox="0 0 120 160" width="140" height="187" aria-hidden="true">
        <defs><clipPath id="glass-clip"><path d="M15 10 H105 L92 150 H28 Z"/></clipPath>
        <linearGradient id="liq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe07a"/><stop offset="1" stop-color="#e8a33d"/></linearGradient></defs>
        <g clip-path="url(#glass-clip)"><rect class="liquid" x="0" y="10" width="120" height="145" fill="url(#liq)"/></g>
        <path d="M15 10 H105 L92 150 H28 Z" fill="none" stroke="#d7e3f4" stroke-width="4" stroke-linejoin="round"/></svg>`,
    })
  );

  const lblWinner = h("div", { class: "winner" });
  const statsBox = h("div", { class: "stats" });
  const panelVictory = h(
    "div",
    { class: "panel center" },
    lblWinner,
    statsBox,
    h(
      "div",
      { class: "actions" },
      h("button", { class: "btn", onclick: showMenu }, "Menu"),
      h("button", { class: "btn primary", onclick: showWizard }, "Nouvelle partie")
    )
  );

  const panelFinal = h(
    "div",
    { class: "panel" },
    h("div", { class: "final-title" }, "⭐ QUESTION ULTIME ⭐"),
    h("p", { class: "center-text" }, "Adversaires, choisissez le thème !"),
    h(
      "div",
      { class: "stack" },
      themes.map((t) =>
        h(
          "button",
          {
            class: "btn big",
            style: { background: safeColor(t.color), color: textOn(safeColor(t.color)), borderColor: "transparent" },
            onclick: () => chooseFinalTheme(t.id),
          },
          t.name
        )
      )
    )
  );

  const panels = { wheel: panelWheel, question: panelQuestion, shot: panelShot, victory: panelVictory, final: panelFinal };
  const stage = h("main", { class: "stage" }, Object.values(panels));
  const setStage = (name) => Object.entries(panels).forEach(([k, el]) => (el.hidden = k !== name));

  const node = h(
    "section",
    { class: "screen game" },
    h(
      "header",
      { class: "game-top" },
      h("button", { class: "btn small ghost", onclick: abandon, "aria-label": "Abandonner la partie" }, "✕ Quitter"),
      lblTurn
    ),
    playersBar,
    stage,
    lblInstruction
  );

  // --- rendering ---
  function renderPlayers() {
    playersBar.replaceChildren(
      ...engine.players.map((p, i) =>
        h("div", { class: "player" + (i === engine.currentPlayerIndex ? " active" : "") }, [
          h("span", { html: diskSVG(themes, p.wedges, p.awaitingFinal) }),
          h("span", { class: "pname", style: { color: safeColor(p.color) } }, p.name),
        ])
      )
    );
  }

  function render() {
    const state = engine.state;
    const player = engine.currentPlayer;
    renderPlayers();

    if (state === State.SHOW_PLAYER) {
      lblTurn.textContent = `Au tour de ${player.name}`;
      lblInstruction.textContent = "Touche la roue (ou ESPACE) pour la lancer";
      setStage("wheel");
    } else if (state === State.FINAL_CHOICE) {
      lblTurn.textContent = `Au tour de ${player.name}`;
      lblInstruction.textContent = "Les adversaires choisissent le thème de la question ultime";
      setStage("final");
    } else if (state === State.SPINNING) {
      lblInstruction.textContent = "La roue tourne…";
      setStage("wheel");
    } else if (state === State.QUESTION || state === State.ANSWER) {
      const theme = themes.find((t) => t.id === engine.currentThemeId);
      qTheme.textContent = (engine.isFinal ? "⭐ QUESTION ULTIME — " : "") + (theme ? theme.name : "");
      qTheme.style.color = theme ? safeColor(theme.color) : "";
      qText.textContent = engine.currentQuestion.question;
      const answered = state === State.ANSWER;
      aText.textContent = answered ? `Réponse : ${engine.currentQuestion.answer}` : "";
      aText.hidden = !answered;
      btnReveal.hidden = answered;
      btnOk.hidden = !answered;
      btnKo.hidden = !answered;
      btnOk.disabled = btnKo.disabled = false;
      lblInstruction.textContent = answered
        ? "Bonne ou mauvaise réponse ?"
        : "Réponds à voix haute, puis touche pour révéler la réponse";
      setStage("question");
    } else if (state === State.GAME_OVER) {
      renderVictory();
    }
  }

  function renderVictory() {
    store.clearGame();
    lblTurn.textContent = "Partie terminée";
    lblInstruction.textContent = "";
    lblWinner.textContent = `🎉 ${engine.winner.name} remporte la partie ! 🎉`;
    const ranking = [...engine.players].sort((a, b) => b.correct - a.correct || b.wedges.size - a.wedges.size);
    statsBox.replaceChildren(
      ...ranking.map((p) =>
        h(
          "div",
          { class: "stat-row" },
          h("strong", { style: { color: safeColor(p.color) } }, p.name),
          ` — ✅ ${p.correct} · 🥃 ${p.wrong} · 🧩 ${p.wedges.size}/${themes.length}`
        )
      )
    );
    renderPlayers();
    sound.play("victory");
    setStage("victory");
  }

  // --- interaction ---
  function primary() {
    if (busy || destroyed) return;
    if (engine.state === State.SHOW_PLAYER && !wheel.spinning) startSpin();
    else if (engine.state === State.QUESTION) reveal();
  }

  function startSpin() {
    const theme = engine.spinTheme();
    lblInstruction.textContent = "La roue tourne…";
    sound.play("spin");
    wheel.spinTo(themes.indexOf(theme), store.getSetting("wheel_duration_ms")).then(() => {
      if (destroyed) return;
      sound.play("land");
      engine.drawQuestion();
      render();
    });
  }

  function chooseFinalTheme(themeId) {
    if (engine.state !== State.FINAL_CHOICE) return;
    sound.play("click");
    engine.drawFinalQuestion(themeId);
    render();
  }

  function reveal() {
    if (engine.state !== State.QUESTION) return;
    sound.play("click");
    engine.revealAnswer();
    render();
  }

  function answer(correct) {
    if (engine.state !== State.ANSWER || busy) return;
    busy = true;
    btnOk.disabled = btnKo.disabled = true;
    const result = engine.recordAnswer(correct);
    if (correct) {
      sound.play(result.wedgeAdded ? "wedge" : "correct");
      renderPlayers();
      if (result.won) later(render, 400);
      else later(advanceTurn, 900);
    } else {
      sound.play("shot");
      renderPlayers();
      lblInstruction.textContent = "";
      setStage("shot"); // the panel becomes visible, which restarts the CSS animation
      panelShot.classList.add("play");
      later(advanceTurn, 1800);
    }
  }

  function advanceTurn() {
    busy = false;
    if (engine.state === State.GAME_OVER) return render();
    engine.nextTurn();
    render();
    save();
  }

  function save() {
    if (engine.state !== State.GAME_OVER) store.saveGame(engine.toJSON());
  }

  async function abandon() {
    sound.play("click");
    if (engine.state === State.GAME_OVER) return showMenu();
    const ok = await confirmBox(
      "Quitter la partie ? Elle reste sauvegardée au début du tour en cours : tu pourras la reprendre depuis le menu.",
      { ok: "Quitter" }
    );
    if (!ok) return;
    showMenu();
  }

  // --- lifecycle ---
  const onKey = (e) => {
    if (e.code === "Space" && !e.target.closest("button, input, textarea, dialog")) {
      e.preventDefault();
      primary();
    }
  };
  document.addEventListener("keydown", onKey);

  let wakeLock = null;
  const requestWake = async () => {
    try {
      if ("wakeLock" in navigator && !destroyed) wakeLock = await navigator.wakeLock.request("screen");
    } catch (e) { /* not available */ }
  };
  const onVisible = () => document.visibilityState === "visible" && requestWake();
  document.addEventListener("visibilitychange", onVisible);
  requestWake();

  show(node, () => {
    destroyed = true;
    timers.forEach(clearTimeout);
    wheel.destroy();
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVisible);
    if (wakeLock) wakeLock.release().catch(() => {});
  });

  render();
  save();
}

// ---------------------------------------------------------------------------
// Questions manager
// ---------------------------------------------------------------------------

function showQuestions(themeId = null) {
  sound.play("click");
  return themeId == null ? showThemeList() : showThemeDetail(themeId);
}

function showThemeList() {
  const fileInput = h("input", {
    type: "file",
    accept: ".xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    hidden: true,
    onchange: async (e) => {
      const file = e.target.files[0];
      e.target.value = "";
      if (file) await importExcel(file);
    },
  });

  const listBox = h("div", { class: "stack" });
  const fillList = () => {
    const themes = store.listThemes();
    listBox.replaceChildren(
      ...(themes.length
        ? themes.map((t) =>
            h(
              "button",
              { class: "theme-pick", onclick: () => showQuestions(t.id) },
              h("span", { class: "dot", style: { background: safeColor(t.color) } }),
              h("span", { class: "grow" }, t.name),
              h("span", { class: "muted" }, `${store.countQuestions(t.id)}`),
              h("span", { class: "chev" }, "›")
            )
          )
        : [h("p", { class: "hint" }, "Aucun thème. Importe un fichier Excel ou crée un thème.")])
    );
  };

  async function importExcel(file) {
    try {
      const sheets = xl.parseWorkbook(await file.arrayBuffer());
      if (!sheets.length) return toast("Aucune question trouvée dans ce fichier.");
      const rows = sheets.map((s) => ({ s, checked: true, fresh: store.countNew(s.name, s.pairs) }));
      const body = h(
        "div",
        { class: "stack" },
        h(
          "p",
          { class: "hint" },
          "Chaque feuille devient un thème (créé s'il n'existe pas). Les questions déjà présentes sont ignorées."
        ),
        rows.map((r) =>
          h(
            "label",
            { class: "check-row" },
            h("input", { type: "checkbox", checked: true, onchange: (e) => (r.checked = e.target.checked) }),
            h("span", {}, `${r.s.name} — ${r.s.pairs.length} question(s), dont ${r.fresh} nouvelle(s)`)
          )
        )
      );
      const res = await modal({
        title: "Importer depuis Excel",
        body,
        actions: [
          { id: "cancel", label: "Annuler" },
          { id: "ok", label: "Importer", class: "primary" },
        ],
      });
      if (res !== "ok") return;
      let added = 0;
      let skipped = 0;
      let themes = 0;
      for (const r of rows) {
        if (!r.checked) continue;
        const theme = store.getOrCreateTheme(r.s.name);
        const out = store.bulkAdd(theme.id, r.s.pairs);
        added += out.added;
        skipped += out.skipped;
        themes++;
      }
      sound.play("correct");
      toast(`${added} question(s) ajoutée(s) dans ${themes} thème(s)` + (skipped ? `, ${skipped} doublon(s) ignoré(s).` : "."));
      fillList();
    } catch (e) {
      console.error(e);
      toast("Fichier illisible : " + (e.message || e));
    }
  }

  function exportExcel() {
    if (!store.listThemes().length) return toast("Rien à exporter pour l'instant.");
    const { file, themes, questions } = xl.buildExport(store);
    xl.downloadFile(file);
    toast(`${questions} question(s) exportée(s) dans ${themes} feuille(s).`);
  }

  async function shareExcel() {
    if (!store.listThemes().length) return toast("Rien à exporter pour l'instant.");
    const { file } = xl.buildExport(store);
    if (!xl.canShareFile(file)) {
      xl.downloadFile(file);
      return toast("Partage indisponible : fichier téléchargé.");
    }
    try {
      await xl.shareFile(file);
    } catch (e) {
      xl.downloadFile(file);
      toast("Partage impossible : fichier téléchargé.");
    }
  }

  async function addTheme() {
    const name = await promptBox("Nouveau thème", "Nom du thème");
    if (!name) return;
    try {
      const t = store.addTheme(name);
      showQuestions(t.id);
    } catch (e) {
      toast(e.message === "exists" ? "Ce thème existe déjà." : "Nom invalide.");
    }
  }

  fillList();
  show(
    h(
      "section",
      { class: "screen" },
      h("header", { class: "bar" }, h("button", { class: "btn small", onclick: showMenu }, "‹ Menu"), h("h1", {}, "Questions")),
      h(
        "div",
        { class: "toolbar" },
        h("button", { class: "btn primary", onclick: () => fileInput.click() }, "📥 Importer Excel"),
        h("button", { class: "btn", onclick: exportExcel }, "📤 Exporter Excel"),
        navigator.share && h("button", { class: "btn", onclick: shareExcel }, "Partager…"),
        h("button", { class: "btn", onclick: addTheme }, "+ Thème")
      ),
      fileInput,
      listBox,
      h(
        "p",
        { class: "hint" },
        "Astuce : l'export Excel sert aussi de sauvegarde et permet de transférer tes questions entre le PC et le téléphone."
      )
    )
  );
}

function showThemeDetail(themeId) {
  const theme = store.getTheme(themeId);
  if (!theme) return showThemeList();

  const search = h("input", {
    type: "search",
    class: "field",
    placeholder: "Rechercher une question…",
    oninput: fillList,
  });
  const listBox = h("div", { class: "stack" });
  const countLbl = h("span", { class: "muted" });

  function fillList() {
    const needle = search.value.trim().toLowerCase();
    const all = store.listQuestions(themeId);
    const shown = all.filter(
      (q) => !needle || q.question.toLowerCase().includes(needle) || q.answer.toLowerCase().includes(needle)
    );
    countLbl.textContent = needle ? `${shown.length} / ${all.length} question(s)` : `${all.length} question(s)`;
    listBox.replaceChildren(
      ...(shown.length
        ? shown.map((q) =>
            h(
              "button",
              { class: "q-row", onclick: () => editQuestion(q) },
              h("span", { class: "q" }, q.question),
              h("span", { class: "a" }, q.answer)
            )
          )
        : [h("p", { class: "hint" }, all.length ? "Aucun résultat." : "Aucune question dans ce thème.")])
    );
  }

  async function questionDialog(title, q = "", a = "", withDelete = false) {
    const tq = h("textarea", { class: "field", rows: "3" }, q);
    const ta = h("textarea", { class: "field", rows: "3" }, a);
    const actions = [{ id: "cancel", label: "Annuler" }];
    if (withDelete) actions.unshift({ id: "delete", label: "Supprimer", class: "danger" });
    actions.push({
      id: "ok",
      label: "Enregistrer",
      class: "primary",
      validate: () => {
        if (tq.value.trim() && ta.value.trim()) return true;
        toast("La question et la réponse sont obligatoires.");
        return false;
      },
    });
    const res = await modal({
      title,
      body: h("div", { class: "stack" }, h("label", { class: "stack" }, "Question", tq), h("label", { class: "stack" }, "Réponse", ta)),
      actions,
    });
    return { res, q: tq.value, a: ta.value };
  }

  async function addQuestion() {
    const { res, q, a } = await questionDialog("Nouvelle question");
    if (res === "ok") {
      store.addQuestion(themeId, q, a);
      fillList();
      toast("Question ajoutée.");
    }
  }

  async function editQuestion(question) {
    const { res, q, a } = await questionDialog("Modifier la question", question.question, question.answer, true);
    if (res === "ok") {
      store.updateQuestion(question.id, q, a);
      fillList();
    } else if (res === "delete") {
      if (await confirmBox("Supprimer cette question ?", { ok: "Supprimer", danger: true })) {
        store.deleteQuestion(question.id);
        fillList();
      }
    }
  }

  async function renameTheme() {
    const name = await promptBox("Renommer le thème", "Nouveau nom", theme.name);
    if (!name) return;
    try {
      store.renameTheme(themeId, name);
      showThemeDetail(themeId);
    } catch (e) {
      toast(e.message === "exists" ? "Ce thème existe déjà." : "Nom invalide.");
    }
  }

  async function deleteTheme() {
    if (await confirmBox(`Supprimer le thème « ${theme.name} » et toutes ses questions ?`, { ok: "Supprimer", danger: true })) {
      store.deleteTheme(themeId);
      showThemeList();
    }
  }

  fillList();
  show(
    h(
      "section",
      { class: "screen" },
      h(
        "header",
        { class: "bar" },
        h("button", { class: "btn small", onclick: () => showThemeList() }, "‹ Thèmes"),
        h("h1", {}, h("span", { class: "dot", style: { background: safeColor(theme.color) } }), theme.name)
      ),
      h(
        "div",
        { class: "toolbar" },
        h("button", { class: "btn primary", onclick: addQuestion }, "+ Question"),
        h("button", { class: "btn", onclick: renameTheme }, "Renommer"),
        h(
          "label",
          { class: "btn color-btn" },
          "Couleur",
          h("input", {
            type: "color",
            value: safeColor(theme.color),
            onchange: (e) => {
              store.setThemeColor(themeId, e.target.value);
              showThemeDetail(themeId);
            },
          })
        ),
        h("button", { class: "btn danger", onclick: deleteTheme }, "Supprimer")
      ),
      search,
      countLbl,
      listBox
    )
  );
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

function showSettings() {
  sound.play("click");
  const volLabel = h("span", { class: "muted" }, `${store.getSetting("volume")} %`);
  const durLabel = h("span", { class: "muted" }, `${store.getSetting("wheel_duration_ms") / 1000} s`);

  const node = h(
    "section",
    { class: "screen" },
    h("header", { class: "bar" }, h("button", { class: "btn small", onclick: showMenu }, "‹ Menu"), h("h1", {}, "Paramètres")),
    h(
      "div",
      { class: "stack form" },
      h(
        "label",
        { class: "check-row" },
        h("input", {
          type: "checkbox",
          checked: store.getSetting("sound_enabled"),
          onchange: (e) => {
            store.setSetting("sound_enabled", e.target.checked);
            sound.play("click");
          },
        }),
        h("span", {}, "Activer les sons")
      ),
      h(
        "label",
        { class: "stack" },
        h("span", {}, "Volume ", volLabel),
        h("input", {
          type: "range",
          min: "0",
          max: "100",
          value: String(store.getSetting("volume")),
          oninput: (e) => {
            store.setSetting("volume", Number(e.target.value));
            volLabel.textContent = `${e.target.value} %`;
          },
          onchange: () => sound.play("correct"),
        })
      ),
      h(
        "label",
        { class: "stack" },
        h("span", {}, "Durée de la roue ", durLabel),
        h("input", {
          type: "range",
          min: "1",
          max: "6",
          step: "0.5",
          value: String(store.getSetting("wheel_duration_ms") / 1000),
          oninput: (e) => {
            store.setSetting("wheel_duration_ms", Math.round(Number(e.target.value) * 1000));
            durLabel.textContent = `${e.target.value} s`;
          },
        })
      ),
      h(
        "label",
        { class: "check-row" },
        h("input", {
          type: "checkbox",
          checked: store.getSetting("avoid_repeats"),
          onchange: (e) => store.setSetting("avoid_repeats", e.target.checked),
        }),
        h("span", {}, "Éviter de reposer une question déjà posée pendant la partie")
      ),
      h(
        "label",
        { class: "stack" },
        "Thème visuel",
        h(
          "select",
          {
            class: "field",
            onchange: (e) => {
              store.setSetting("ui_theme", e.target.value);
              applyTheme();
            },
          },
          h("option", { value: "dark", selected: store.getSetting("ui_theme") === "dark" }, "Sombre"),
          h("option", { value: "light", selected: store.getSetting("ui_theme") === "light" }, "Clair")
        )
      ),
      h(
        "button",
        {
          class: "btn danger",
          onclick: async () => {
            if (await confirmBox("Ceci supprimera définitivement tous les thèmes et toutes les questions de cet appareil. Pense à exporter en Excel avant. Continuer ?", { ok: "Tout supprimer", danger: true })) {
              store.resetBank();
              toast("Banque de questions réinitialisée.");
            }
          },
        },
        "Réinitialiser la banque de questions"
      ),
      h("p", { class: "hint" }, "Les données sont enregistrées sur cet appareil uniquement. Utilise « Exporter Excel » dans l'écran Questions pour les sauvegarder ou les copier sur un autre appareil.")
    )
  );
  show(node);
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

["pointerup", "click", "keydown"].forEach((evt) => document.addEventListener(evt, () => sound.unlock(), { passive: true }));
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstall = e;
  if (root.querySelector(".menu")) showMenu();
});
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch((e) => console.warn("Service worker non enregistré", e));
}
store.requestPersistence();
applyTheme();
showMenu();

// Exposed for automated tests only.
window.__tp = { store, showMenu };
