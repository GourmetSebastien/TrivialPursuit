from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget


class MainMenuScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        title = QLabel("Trivial Pursuit — Entre Potes")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Le quiz maison, entre amis")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        self.btn_resume = QPushButton("Reprendre la partie")
        self.btn_resume.setObjectName("menuButtonPrimary")
        self.btn_resume.clicked.connect(self._go_resume)
        layout.addWidget(self.btn_resume)

        btn_new_game = QPushButton("Nouvelle partie")
        btn_new_game.setObjectName("menuButton")
        btn_new_game.clicked.connect(self._go_new_game)
        layout.addWidget(btn_new_game)

        btn_questions = QPushButton("Questions")
        btn_questions.setObjectName("menuButton")
        btn_questions.clicked.connect(self._go_questions)
        layout.addWidget(btn_questions)

        btn_settings = QPushButton("Paramètres")
        btn_settings.setObjectName("menuButton")
        btn_settings.clicked.connect(self._go_settings)
        layout.addWidget(btn_settings)

        btn_quit = QPushButton("Fermer le jeu")
        btn_quit.setObjectName("menuButtonDanger")
        btn_quit.clicked.connect(self._quit)
        layout.addWidget(btn_quit)

        for btn in (self.btn_resume, btn_new_game, btn_questions, btn_settings, btn_quit):
            btn.setMinimumSize(280, 56)
            btn.setCursor(Qt.PointingHandCursor)

    def refresh(self):
        self.btn_resume.setVisible(self.main_window.has_saved_game())

    def _go_resume(self):
        self.main_window.sound.play("click")
        self.main_window.resume_game()

    def _go_new_game(self):
        self.main_window.sound.play("click")
        if self.main_window.has_saved_game():
            reply = QMessageBox.question(
                self,
                "Nouvelle partie",
                "Une partie sauvegardée existe. La nouvelle partie l'écrasera. Continuer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.main_window.show_new_game_wizard()

    def _go_questions(self):
        self.main_window.sound.play("click")
        self.main_window.show_questions()

    def _go_settings(self):
        self.main_window.sound.play("click")
        self.main_window.show_settings()

    def _quit(self):
        self.main_window.sound.play("click")
        reply = QMessageBox.question(
            self,
            "Fermer le jeu",
            "Voulez-vous vraiment quitter ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.main_window.close()
