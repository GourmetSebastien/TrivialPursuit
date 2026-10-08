from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from .db import Database
from .screens.game_screen import GameScreen
from .screens.main_menu import MainMenuScreen
from .screens.new_game_wizard import NewGameWizard
from .screens.questions_manager import QuestionsManagerScreen
from .screens.settings_screen import SettingsScreen
from .sound_manager import SoundManager
from .stylesheets import DARK_STYLE, LIGHT_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trivial Pursuit — Entre Potes")
        self.resize(1280, 820)

        self.db = Database()
        self.sound = SoundManager(self.db)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_menu = MainMenuScreen(self)
        self.questions_screen = QuestionsManagerScreen(self)
        self.settings_screen = SettingsScreen(self)
        self.new_game_wizard = NewGameWizard(self)
        self.game_screen = None

        for widget in (self.main_menu, self.questions_screen, self.settings_screen, self.new_game_wizard):
            self.stack.addWidget(widget)

        self.apply_settings()
        self.show_main_menu()

    # ------------------------------------------------------------------

    def apply_settings(self):
        theme = self.db.get_setting("ui_theme", "dark")
        self.setStyleSheet(DARK_STYLE if theme == "dark" else LIGHT_STYLE)

        fullscreen = self.db.get_setting("fullscreen", "0") == "1"
        if fullscreen:
            self.showFullScreen()
        elif self.isFullScreen():
            self.showNormal()

        self.sound.set_volume(int(self.db.get_setting("volume", "80")))
        self.sound.set_muted(self.db.get_setting("sound_enabled", "1") == "0")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_main_menu(self):
        self.questions_screen.refresh()
        self.main_menu.refresh()
        self.stack.setCurrentWidget(self.main_menu)

    def show_questions(self):
        self.questions_screen.refresh()
        self.stack.setCurrentWidget(self.questions_screen)

    def show_settings(self):
        self.settings_screen.refresh()
        self.stack.setCurrentWidget(self.settings_screen)

    def show_new_game_wizard(self):
        if self.game_screen is not None:
            self.stack.removeWidget(self.game_screen)
            self.game_screen.deleteLater()
            self.game_screen = None
        self.new_game_wizard.reset()
        self.stack.setCurrentWidget(self.new_game_wizard)

    def start_game(self, players, themes, saved=None):
        if self.game_screen is not None:
            self.stack.removeWidget(self.game_screen)
            self.game_screen.deleteLater()
        self.game_screen = GameScreen(self, players, themes, saved)
        self.stack.addWidget(self.game_screen)
        self.stack.setCurrentWidget(self.game_screen)
        self.game_screen.setFocus()

    def has_saved_game(self) -> bool:
        return self.db.load_game() is not None

    def resume_game(self):
        saved = self.db.load_game()
        themes_by_id = {t.id: t for t in self.db.list_themes()}
        try:
            themes = [themes_by_id[tid] for tid in saved["theme_ids"]]
            if any(self.db.count_questions(t.id) == 0 for t in themes):
                raise KeyError("thème sans question")
            self.start_game(None, themes, saved)
        except (KeyError, TypeError, ValueError):
            self.db.clear_saved_game()
            QMessageBox.warning(
                self,
                "Reprendre la partie",
                "La partie sauvegardée n'est plus valide (thèmes ou questions supprimés).",
            )
            self.show_main_menu()

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)

    def end_game_to_menu(self):
        self.show_main_menu()
