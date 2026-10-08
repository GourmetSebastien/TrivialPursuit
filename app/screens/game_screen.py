from html import escape
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..db import Database
from ..game_engine import GameEngine, GameState
from ..models import Theme
from ..widgets.player_disk_widget import PlayerDiskWidget
from ..widgets.shot_glass_widget import ShotGlassWidget
from ..widgets.wheel_widget import WheelWidget


class GameScreen(QWidget):
    def __init__(self, main_window, players: Optional[list], themes: list, saved: Optional[dict] = None):
        super().__init__()
        self.main_window = main_window
        self.db: Database = main_window.db
        self.sound = main_window.sound
        self.themes = themes

        self.wheel_duration_ms = int(self.db.get_setting("wheel_duration_ms", "3000"))
        avoid_repeats = self.db.get_setting("avoid_repeats", "1") == "1"
        questions_by_theme = {t.id: self.db.list_questions(t.id) for t in themes}
        if saved is not None:
            self.engine = GameEngine.restore(saved, themes, questions_by_theme, avoid_repeats=avoid_repeats)
        else:
            self.engine = GameEngine(players, themes, questions_by_theme, avoid_repeats=avoid_repeats)

        self.player_rows = {}  # player index -> (frame, disk_widget)

        self._build_ui()
        self.setFocusPolicy(Qt.StrongFocus)
        self._render_state()
        self._save_progress()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)

        center = QVBoxLayout()
        root.addLayout(center, 3)

        self.lbl_player = QLabel("")
        self.lbl_player.setObjectName("playerTurnLabel")
        self.lbl_player.setAlignment(Qt.AlignCenter)
        center.addWidget(self.lbl_player)

        self.stage = QStackedWidget()
        center.addWidget(self.stage, 1)

        self.stage.addWidget(self._build_wheel_page())
        self.stage.addWidget(self._build_question_page())
        self.stage.addWidget(self._build_shot_page())
        self.stage.addWidget(self._build_victory_page())
        self.stage.addWidget(self._build_final_choice_page())

        self.lbl_instruction = QLabel("")
        self.lbl_instruction.setObjectName("instructionLabel")
        self.lbl_instruction.setAlignment(Qt.AlignCenter)
        center.addWidget(self.lbl_instruction)

        bottom_row = QHBoxLayout()
        btn_abandon = QPushButton("Abandonner la partie")
        btn_abandon.clicked.connect(self._abandon)
        bottom_row.addWidget(btn_abandon)
        bottom_row.addStretch()
        center.addLayout(bottom_row)

        sidebar = self._build_sidebar()
        root.addWidget(sidebar, 1)

    def _build_wheel_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.wheel = WheelWidget(self.themes)
        self.wheel.landed.connect(self._on_wheel_landed)
        self.wheel.clicked.connect(self._primary_action)
        layout.addWidget(self.wheel, 1, Qt.AlignCenter)
        return page

    def _build_final_choice_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        lbl = QLabel("⭐ QUESTION ULTIME ⭐\nAdversaires, choisissez le thème !")
        lbl.setObjectName("themeNameLabel")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        for theme in self.themes:
            btn = QPushButton(theme.name)
            btn.setMinimumHeight(48)
            btn.setCursor(Qt.PointingHandCursor)
            bg = QColor(theme.color)
            text_color = "#111111" if bg.lightness() > 150 else "white"
            btn.setStyleSheet(f"background-color: {theme.color}; color: {text_color}; font-weight: bold;")
            btn.clicked.connect(lambda _checked=False, tid=theme.id: self._choose_final_theme(tid))
            layout.addWidget(btn)
        layout.addStretch()
        return page

    def _build_question_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_theme_name = QLabel("")
        self.lbl_theme_name.setObjectName("themeNameLabel")
        self.lbl_theme_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_theme_name)

        self.lbl_question = QLabel("")
        self.lbl_question.setWordWrap(True)
        self.lbl_question.setObjectName("questionLabel")
        self.lbl_question.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_question, 1)

        self.lbl_answer = QLabel("")
        self.lbl_answer.setWordWrap(True)
        self.lbl_answer.setObjectName("answerLabel")
        self.lbl_answer.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_answer, 1)

        buttons_row = QHBoxLayout()
        self.btn_reveal = QPushButton("Révéler la réponse")
        self.btn_reveal.setObjectName("menuButtonPrimary")
        self.btn_reveal.clicked.connect(self._reveal_answer)
        buttons_row.addWidget(self.btn_reveal)
        self.btn_correct = QPushButton("Bonne réponse")
        self.btn_correct.setObjectName("menuButtonPrimary")
        self.btn_correct.clicked.connect(lambda: self._answer(True))
        self.btn_wrong = QPushButton("Mauvaise réponse")
        self.btn_wrong.setObjectName("menuButtonDanger")
        self.btn_wrong.clicked.connect(lambda: self._answer(False))
        buttons_row.addWidget(self.btn_correct)
        buttons_row.addWidget(self.btn_wrong)
        layout.addLayout(buttons_row)

        return page

    def _build_shot_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        lbl = QLabel("Mauvaise réponse... cul sec ! 🥃")
        lbl.setObjectName("shotLabel")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        self.shot_glass = ShotGlassWidget()
        layout.addWidget(self.shot_glass, 1, Qt.AlignCenter)
        layout.addStretch()
        return page

    def _build_victory_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        self.lbl_winner = QLabel("")
        self.lbl_winner.setObjectName("winnerLabel")
        self.lbl_winner.setAlignment(Qt.AlignCenter)
        self.lbl_winner.setWordWrap(True)
        layout.addWidget(self.lbl_winner)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setTextFormat(Qt.RichText)
        self.lbl_stats.setAlignment(Qt.AlignCenter)
        self.lbl_stats.setStyleSheet("font-size: 16pt;")
        layout.addWidget(self.lbl_stats)

        buttons_row = QHBoxLayout()
        btn_menu = QPushButton("Retour au menu")
        btn_menu.clicked.connect(self.main_window.end_game_to_menu)
        btn_replay = QPushButton("Nouvelle partie")
        btn_replay.setObjectName("menuButtonPrimary")
        btn_replay.clicked.connect(self.main_window.show_new_game_wizard)
        buttons_row.addStretch()
        buttons_row.addWidget(btn_menu)
        buttons_row.addWidget(btn_replay)
        buttons_row.addStretch()
        layout.addLayout(buttons_row)
        layout.addStretch()
        return page

    def _build_sidebar(self) -> QWidget:
        container = QWidget()
        outer = QVBoxLayout(container)
        title = QLabel("Joueurs")
        title.setObjectName("subtitleLabel")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll, 1)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setAlignment(Qt.AlignTop)

        for index, player in enumerate(self.engine.players):
            frame = QFrame()
            frame.setObjectName("playerRow")
            row = QHBoxLayout(frame)
            disk = PlayerDiskWidget(self.themes, player)
            row.addWidget(disk)
            name_label = QLabel(player.name)
            name_label.setStyleSheet(f"color: {player.color}; font-weight: bold;")
            row.addWidget(name_label, 1)
            inner_layout.addWidget(frame)
            self.player_rows[index] = (frame, disk)

        scroll.setWidget(inner)
        return container

    # ------------------------------------------------------------------
    # State rendering
    # ------------------------------------------------------------------

    def _render_state(self):
        state = self.engine.state
        player = self.engine.current_player
        self._highlight_active_player()

        if state == GameState.SHOW_PLAYER:
            self.lbl_player.setText(f"Au tour de {player.name}")
            self.lbl_instruction.setText("Appuyez sur ESPACE ou cliquez sur la roue pour la lancer")
            self.stage.setCurrentIndex(0)
        elif state == GameState.FINAL_CHOICE:
            self.lbl_player.setText(f"Au tour de {player.name}")
            self.lbl_instruction.setText("Les adversaires choisissent le thème de la question ultime")
            self.stage.setCurrentIndex(4)
        elif state == GameState.SPINNING:
            self.lbl_instruction.setText("La roue tourne…")
            self.stage.setCurrentIndex(0)
        elif state == GameState.QUESTION:
            theme = self._theme_by_id(self.engine.current_theme_id)
            name = theme.name if theme else ""
            self.lbl_theme_name.setText(f"⭐ QUESTION ULTIME — {name}" if self.engine.is_final else name)
            self.lbl_theme_name.setStyleSheet(
                f"color: {theme.color}; font-weight: bold;" if theme else ""
            )
            self.lbl_question.setText(self.engine.current_question.question)
            self.lbl_answer.setText("")
            self.lbl_answer.setVisible(False)
            self.btn_reveal.setVisible(True)
            self.btn_correct.setVisible(False)
            self.btn_wrong.setVisible(False)
            self.lbl_instruction.setText("Répondez à voix haute, puis appuyez sur ESPACE ou cliquez pour révéler la réponse")
            self.stage.setCurrentIndex(1)
        elif state == GameState.ANSWER:
            self.lbl_answer.setText(f"Réponse : {self.engine.current_question.answer}")
            self.lbl_answer.setVisible(True)
            self.btn_reveal.setVisible(False)
            self.btn_correct.setVisible(True)
            self.btn_wrong.setVisible(True)
            self.lbl_instruction.setText("Bonne ou mauvaise réponse ?")
            self.stage.setCurrentIndex(1)
        elif state == GameState.GAME_OVER:
            self._render_victory()

    def _theme_by_id(self, theme_id) -> Theme:
        for t in self.themes:
            if t.id == theme_id:
                return t
        return None

    def _highlight_active_player(self):
        for index, (frame, _disk) in self.player_rows.items():
            active = index == self.engine.current_player_index
            frame.setProperty("active", "true" if active else "false")
            frame.style().unpolish(frame)
            frame.style().polish(frame)

    def _refresh_sidebar(self):
        for _index, (_frame, disk) in self.player_rows.items():
            disk.update()

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self._primary_action()
            event.accept()
            return
        super().keyPressEvent(event)

    def _primary_action(self):
        """Space bar or click: spin the wheel, or reveal the answer."""
        if self.engine.state == GameState.SHOW_PLAYER and not self.wheel.is_spinning():
            self._start_spin()
        elif self.engine.state == GameState.QUESTION:
            self._reveal_answer()

    def _choose_final_theme(self, theme_id: int):
        if self.engine.state != GameState.FINAL_CHOICE:
            return
        self.sound.play("click")
        self.engine.draw_final_question(theme_id)
        self._render_state()
        self.setFocus()

    def _start_spin(self):
        theme = self.engine.spin_theme()
        index = self.themes.index(theme)
        self.lbl_instruction.setText("La roue tourne…")
        self.sound.play("spin")
        self.wheel.spin_to(index, duration_ms=self.wheel_duration_ms)

    def _on_wheel_landed(self, theme_id: int):
        self.sound.play("land")
        self.engine.draw_question()
        self._render_state()

    def _reveal_answer(self):
        self.engine.reveal_answer()
        self._render_state()

    def _answer(self, correct: bool):
        self.btn_correct.setEnabled(False)
        self.btn_wrong.setEnabled(False)
        result = self.engine.record_answer(correct)

        if correct:
            self.sound.play("wedge" if result.wedge_added else "correct")
            self._refresh_sidebar()
            if result.won:
                QTimer.singleShot(400, self._render_state)
            else:
                QTimer.singleShot(900, self._advance_turn)
        else:
            self.sound.play("shot")
            self.stage.setCurrentIndex(2)
            self.lbl_instruction.setText("")
            self.shot_glass.play()
            QTimer.singleShot(1800, self._advance_turn)

    def _advance_turn(self):
        self.btn_correct.setEnabled(True)
        self.btn_wrong.setEnabled(True)
        if self.engine.state == GameState.GAME_OVER:
            self._render_state()
            return
        self.engine.next_turn()
        self._render_state()
        self._save_progress()
        self.setFocus()

    def _save_progress(self):
        if self.engine.state != GameState.GAME_OVER:
            self.db.save_game(self.engine.to_dict())

    def _render_victory(self):
        winner = self.engine.winner
        self.db.clear_saved_game()
        self.lbl_player.setText("Partie terminée")
        self.lbl_instruction.setText("")
        self.lbl_winner.setText(f"🎉 {winner.name} remporte la partie ! 🎉")
        ranking = sorted(self.engine.players, key=lambda p: (p.correct, p.wedge_count()), reverse=True)
        self.lbl_stats.setText(
            "<br>".join(
                f"<span style='color:{p.color}; font-weight:bold'>{escape(p.name)}</span>"
                f" — ✅ {p.correct} bonne(s) · 🥃 {p.wrong} shot(s) · 🧩 {p.wedge_count()}/{len(self.themes)}"
                for p in ranking
            )
        )
        self.sound.play("victory")
        self.stage.setCurrentIndex(3)

    def _abandon(self):
        reply = QMessageBox.question(
            self,
            "Abandonner la partie",
            "Voulez-vous vraiment abandonner cette partie et revenir au menu ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db.clear_saved_game()
            self.main_window.end_game_to_menu()

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
