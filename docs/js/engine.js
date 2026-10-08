// Turn-by-turn state machine. Same rules as the desktop app (app/game_engine.py).
import { pick } from "./util.js";

export const State = {
  SHOW_PLAYER: "SHOW_PLAYER",
  FINAL_CHOICE: "FINAL_CHOICE",
  SPINNING: "SPINNING",
  QUESTION: "QUESTION",
  ANSWER: "ANSWER",
  GAME_OVER: "GAME_OVER",
};

export function newPlayer(name, color) {
  return { name, color, wedges: new Set(), awaitingFinal: false, correct: 0, wrong: 0 };
}

export class GameEngine {
  constructor(players, themes, questionsByTheme, avoidRepeats = true) {
    if (players.length < 2) throw new Error("Il faut au moins 2 joueurs.");
    if (themes.length !== 5) throw new Error("Il faut exactement 5 thèmes.");
    this.players = players;
    this.themes = themes;
    this.themeIds = new Set(themes.map((t) => t.id));
    this.questionsByTheme = questionsByTheme;
    this.avoidRepeats = avoidRepeats;
    this.used = {};
    themes.forEach((t) => (this.used[t.id] = new Set()));

    this.currentPlayerIndex = 0;
    this.state = State.SHOW_PLAYER;
    this.currentThemeId = null;
    this.currentQuestion = null;
    this.winner = null;
    this.isFinal = false;
  }

  get currentPlayer() {
    return this.players[this.currentPlayerIndex];
  }

  toJSON() {
    return {
      players: this.players.map((p) => ({
        name: p.name,
        color: p.color,
        wedges: [...p.wedges].sort((a, b) => a - b),
        awaiting_final: p.awaitingFinal,
        correct: p.correct,
        wrong: p.wrong,
      })),
      theme_ids: this.themes.map((t) => t.id),
      current_player_index: this.currentPlayerIndex,
      used_question_ids: Object.fromEntries(
        Object.entries(this.used).map(([k, v]) => [k, [...v].sort((a, b) => a - b)])
      ),
    };
  }

  static restore(data, themes, questionsByTheme, avoidRepeats = true) {
    const players = data.players.map((p) => ({
      name: p.name,
      color: p.color,
      wedges: new Set(p.wedges),
      awaitingFinal: !!p.awaiting_final,
      correct: p.correct || 0,
      wrong: p.wrong || 0,
    }));
    const engine = new GameEngine(players, themes, questionsByTheme, avoidRepeats);
    engine.currentPlayerIndex = data.current_player_index % players.length;
    for (const [key, ids] of Object.entries(data.used_question_ids || {})) {
      engine.used[Number(key)] = new Set(ids);
    }
    engine._enterTurn();
    return engine;
  }

  _enterTurn() {
    this.state = this.currentPlayer.awaitingFinal ? State.FINAL_CHOICE : State.SHOW_PLAYER;
  }

  spinTheme() {
    const theme = pick(this.themes);
    this.currentThemeId = theme.id;
    this.state = State.SPINNING;
    return theme;
  }

  drawQuestion() {
    const themeId = this.currentThemeId;
    const pool = this.questionsByTheme[themeId] || [];
    if (!pool.length) throw new Error("Aucune question disponible pour ce thème.");
    const used = (this.used[themeId] = this.used[themeId] || new Set());
    let candidates = this.avoidRepeats ? pool.filter((q) => !used.has(q.id)) : pool;
    if (!candidates.length) {
      used.clear();
      candidates = pool;
    }
    const question = pick(candidates);
    used.add(question.id);
    this.currentQuestion = question;
    this.state = State.QUESTION;
    return question;
  }

  /** Ultimate question: the opponents pick the theme. */
  drawFinalQuestion(themeId) {
    if (!this.themeIds.has(themeId)) throw new Error("Thème inconnu.");
    this.currentThemeId = themeId;
    this.isFinal = true;
    return this.drawQuestion();
  }

  revealAnswer() {
    this.state = State.ANSWER;
  }

  recordAnswer(correct) {
    const player = this.currentPlayer;
    const themeId = this.currentThemeId;
    const result = { correct, wedgeAdded: false, alreadyOwned: false, won: false };

    if (correct) {
      player.correct++;
      if (this.isFinal) {
        result.won = true;
        this.winner = player;
        this.state = State.GAME_OVER;
      } else if (!player.wedges.has(themeId)) {
        player.wedges.add(themeId);
        result.wedgeAdded = true;
        if (player.wedges.size === this.themeIds.size) player.awaitingFinal = true;
      } else {
        result.alreadyOwned = true;
      }
    } else {
      player.wrong++;
    }

    this.isFinal = false;
    if (!result.won) this.state = State.SHOW_PLAYER;
    return result;
  }

  nextTurn() {
    if (this.state === State.GAME_OVER) return;
    this.currentPlayerIndex = (this.currentPlayerIndex + 1) % this.players.length;
    this.currentThemeId = null;
    this.currentQuestion = null;
    this._enterTurn();
  }
}
