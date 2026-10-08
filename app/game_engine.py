import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set

from .models import Player, Question, Theme


class GameState(Enum):
    SHOW_PLAYER = auto()
    FINAL_CHOICE = auto()
    SPINNING = auto()
    QUESTION = auto()
    ANSWER = auto()
    GAME_OVER = auto()


@dataclass
class AnswerResult:
    correct: bool
    wedge_added: bool
    already_owned: bool
    won: bool


class GameEngine:
    """Runs the turn-by-turn state machine for a single game."""

    def __init__(self, players: List[Player], themes: List[Theme], questions_by_theme: Dict[int, List[Question]], avoid_repeats: bool = True):
        if len(players) < 2:
            raise ValueError("Il faut au moins 2 joueurs.")
        if len(themes) != 5:
            raise ValueError("Il faut exactement 5 thèmes.")
        self.players = players
        self.themes = themes
        self.theme_ids: Set[int] = {t.id for t in themes}
        self.questions_by_theme = questions_by_theme
        self.avoid_repeats = avoid_repeats
        self.used_question_ids: Dict[int, Set[int]] = {t.id: set() for t in themes}

        self.current_player_index = 0
        self.state = GameState.SHOW_PLAYER
        self.current_theme_id: Optional[int] = None
        self.current_question: Optional[Question] = None
        self.winner: Optional[Player] = None
        self.is_final = False

    # ------------------------------------------------------------------
    # Save / restore
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "players": [
                {
                    "name": p.name,
                    "color": p.color,
                    "wedges": sorted(p.wedges),
                    "awaiting_final": p.awaiting_final,
                    "correct": p.correct,
                    "wrong": p.wrong,
                }
                for p in self.players
            ],
            "theme_ids": [t.id for t in self.themes],
            "current_player_index": self.current_player_index,
            "used_question_ids": {str(k): sorted(v) for k, v in self.used_question_ids.items()},
        }

    @classmethod
    def restore(cls, data: dict, themes: List[Theme], questions_by_theme: Dict[int, List[Question]], avoid_repeats: bool = True) -> "GameEngine":
        players = [
            Player(
                name=p["name"],
                color=p["color"],
                wedges=set(p["wedges"]),
                awaiting_final=p["awaiting_final"],
                correct=p.get("correct", 0),
                wrong=p.get("wrong", 0),
            )
            for p in data["players"]
        ]
        engine = cls(players, themes, questions_by_theme, avoid_repeats=avoid_repeats)
        engine.current_player_index = data["current_player_index"] % len(players)
        for key, ids in data.get("used_question_ids", {}).items():
            engine.used_question_ids[int(key)] = set(ids)
        engine._enter_turn()
        return engine

    def _enter_turn(self):
        self.state = GameState.FINAL_CHOICE if self.current_player.awaiting_final else GameState.SHOW_PLAYER

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    def spin_theme(self) -> Theme:
        """Pick the theme the wheel will land on for this turn."""
        theme = random.choice(self.themes)
        self.current_theme_id = theme.id
        self.state = GameState.SPINNING
        return theme

    def draw_question(self) -> Question:
        theme_id = self.current_theme_id
        pool = self.questions_by_theme.get(theme_id, [])
        if not pool:
            raise RuntimeError("Aucune question disponible pour ce thème.")
        used = self.used_question_ids.setdefault(theme_id, set())
        candidates = [q for q in pool if q.id not in used] if self.avoid_repeats else pool
        if not candidates:
            used.clear()
            candidates = pool
        question = random.choice(candidates)
        used.add(question.id)
        self.current_question = question
        self.state = GameState.QUESTION
        return question

    def draw_final_question(self, theme_id: int) -> Question:
        """Ultimate question: the opponents pick the theme."""
        if theme_id not in self.theme_ids:
            raise ValueError("Thème inconnu.")
        self.current_theme_id = theme_id
        self.is_final = True
        return self.draw_question()

    def reveal_answer(self):
        self.state = GameState.ANSWER

    def record_answer(self, correct: bool) -> AnswerResult:
        player = self.current_player
        theme_id = self.current_theme_id
        wedge_added = False
        already_owned = False
        won = False

        if correct:
            player.correct += 1
            if self.is_final:
                won = True
                self.winner = player
                self.state = GameState.GAME_OVER
            elif theme_id not in player.wedges:
                player.wedges.add(theme_id)
                wedge_added = True
                if len(player.wedges) == len(self.theme_ids):
                    player.awaiting_final = True
            else:
                already_owned = True
        else:
            player.wrong += 1

        self.is_final = False
        if not won:
            self.state = GameState.SHOW_PLAYER

        return AnswerResult(correct=correct, wedge_added=wedge_added, already_owned=already_owned, won=won)

    def next_turn(self):
        if self.state == GameState.GAME_OVER:
            return
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.current_theme_id = None
        self.current_question = None
        self._enter_turn()
