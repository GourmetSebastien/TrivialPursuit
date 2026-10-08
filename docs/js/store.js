// Data layer: themes, questions, settings and the saved game.
// Everything lives in the browser's localStorage, on this device only.

const DATA_KEY = "tp_data_v1";
const SAVE_KEY = "tp_save_v1";

export const THEME_PALETTE = [
  "#8B4513", "#1E90FF", "#FF1493", "#228B22", "#FFD700", "#8A2BE2", "#FF8C00", "#20B2AA",
];
export const PLAYER_PALETTE = [
  "#E63946", "#457B9D", "#2A9D8F", "#F4A261", "#9D4EDD", "#F72585", "#43AA8B", "#F9C74F",
];

const DEFAULT_SETTINGS = {
  sound_enabled: true,
  volume: 80,
  wheel_duration_ms: 3000,
  avoid_repeats: true,
  ui_theme: "dark",
};

let data = null;

function blank() {
  return { themes: [], questions: [], nextThemeId: 1, nextQuestionId: 1, settings: { ...DEFAULT_SETTINGS } };
}

function load() {
  if (data) return data;
  try {
    const raw = localStorage.getItem(DATA_KEY);
    data = raw ? JSON.parse(raw) : blank();
  } catch (e) {
    console.warn("Lecture du stockage impossible", e);
    data = blank();
  }
  data.settings = { ...DEFAULT_SETTINGS, ...(data.settings || {}) };
  return data;
}

function persist() {
  try {
    localStorage.setItem(DATA_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn("Écriture du stockage impossible", e);
  }
}

const norm = (s) => String(s).trim().toLowerCase();

export const store = {
  /** Ask the browser not to evict our data when storage is low. */
  async requestPersistence() {
    try {
      if (navigator.storage && navigator.storage.persist) return await navigator.storage.persist();
    } catch (e) { /* not supported */ }
    return false;
  },

  // ---------- Themes ----------
  listThemes() {
    return [...load().themes].sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
  },
  getTheme(id) {
    return load().themes.find((t) => t.id === id) || null;
  },
  nextThemeColor() {
    const used = new Set(load().themes.map((t) => t.color.toLowerCase()));
    const free = THEME_PALETTE.find((c) => !used.has(c.toLowerCase()));
    return free || THEME_PALETTE[used.size % THEME_PALETTE.length];
  },
  addTheme(name, color) {
    const d = load();
    name = name.trim();
    if (!name) throw new Error("empty");
    if (d.themes.some((t) => norm(t.name) === norm(name))) throw new Error("exists");
    const theme = { id: d.nextThemeId++, name, color: color || this.nextThemeColor() };
    d.themes.push(theme);
    persist();
    return theme;
  },
  getOrCreateTheme(name) {
    const found = load().themes.find((t) => norm(t.name) === norm(name));
    return found || this.addTheme(name);
  },
  renameTheme(id, name) {
    const d = load();
    name = name.trim();
    if (!name) throw new Error("empty");
    if (d.themes.some((t) => t.id !== id && norm(t.name) === norm(name))) throw new Error("exists");
    const t = d.themes.find((x) => x.id === id);
    if (t) t.name = name;
    persist();
  },
  setThemeColor(id, color) {
    const t = load().themes.find((x) => x.id === id);
    if (t) t.color = color;
    persist();
  },
  deleteTheme(id) {
    const d = load();
    d.themes = d.themes.filter((t) => t.id !== id);
    d.questions = d.questions.filter((q) => q.theme_id !== id);
    persist();
  },

  // ---------- Questions ----------
  listQuestions(themeId) {
    return load().questions.filter((q) => q.theme_id === themeId);
  },
  countQuestions(themeId) {
    return load().questions.reduce((n, q) => n + (q.theme_id === themeId ? 1 : 0), 0);
  },
  totalQuestions() {
    return load().questions.length;
  },
  addQuestion(themeId, question, answer) {
    const d = load();
    const q = { id: d.nextQuestionId++, theme_id: themeId, question: question.trim(), answer: answer.trim() };
    d.questions.push(q);
    persist();
    return q;
  },
  updateQuestion(id, question, answer) {
    const q = load().questions.find((x) => x.id === id);
    if (q) {
      q.question = question.trim();
      q.answer = answer.trim();
      persist();
    }
  },
  deleteQuestion(id) {
    const d = load();
    d.questions = d.questions.filter((q) => q.id !== id);
    persist();
  },
  /** How many of these [question, answer] pairs are not already in the theme named `themeName`. */
  countNew(themeName, pairs) {
    const theme = load().themes.find((t) => norm(t.name) === norm(themeName));
    const existing = new Set(theme ? this.listQuestions(theme.id).map((q) => norm(q.question)) : []);
    const seen = new Set();
    let n = 0;
    for (const [q] of pairs) {
      const k = norm(q);
      if (!existing.has(k) && !seen.has(k)) n++;
      seen.add(k);
    }
    return n;
  },
  /** Add pairs, skipping questions already present in the theme. */
  bulkAdd(themeId, pairs) {
    const d = load();
    const existing = new Set(this.listQuestions(themeId).map((q) => norm(q.question)));
    let added = 0;
    let skipped = 0;
    for (const [question, answer] of pairs) {
      const q = String(question || "").trim();
      const a = String(answer || "").trim();
      if (!q || !a) continue;
      if (existing.has(norm(q))) {
        skipped++;
        continue;
      }
      existing.add(norm(q));
      d.questions.push({ id: d.nextQuestionId++, theme_id: themeId, question: q, answer: a });
      added++;
    }
    persist();
    return { added, skipped };
  },
  resetBank() {
    const d = load();
    d.themes = [];
    d.questions = [];
    persist();
    this.clearGame();
  },

  // ---------- Settings ----------
  getSetting(key) {
    return load().settings[key];
  },
  setSetting(key, value) {
    load().settings[key] = value;
    persist();
  },

  // ---------- Saved game ----------
  saveGame(state) {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn("Sauvegarde de la partie impossible", e);
    }
  },
  loadGame() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  },
  clearGame() {
    try {
      localStorage.removeItem(SAVE_KEY);
    } catch (e) { /* ignore */ }
  },
};
