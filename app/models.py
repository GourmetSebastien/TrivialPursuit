from dataclasses import dataclass, field
from typing import Set

THEME_PALETTE = [
    "#8B4513",  # marron
    "#1E90FF",  # bleu
    "#FF1493",  # rose
    "#228B22",  # vert
    "#FFD700",  # jaune
    "#8A2BE2",  # violet
    "#FF8C00",  # orange
    "#20B2AA",  # turquoise
]

PLAYER_PALETTE = [
    "#E63946",
    "#457B9D",
    "#2A9D8F",
    "#F4A261",
    "#9D4EDD",
    "#F72585",
    "#43AA8B",
    "#F9C74F",
]


@dataclass
class Theme:
    id: int
    name: str
    color: str


@dataclass
class Question:
    id: int
    theme_id: int
    question: str
    answer: str


@dataclass
class Player:
    name: str
    color: str
    wedges: Set[int] = field(default_factory=set)
    awaiting_final: bool = False
    correct: int = 0
    wrong: int = 0

    def has_wedge(self, theme_id: int) -> bool:
        return theme_id in self.wedges

    def wedge_count(self) -> int:
        return len(self.wedges)
