from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..models import Player


MIN_PLAYERS = 2
REQUIRED_THEMES = 5


class NewGameWizard(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = main_window.db
        self.player_name_edits = []

        root = QVBoxLayout(self)
        title = QLabel("Nouvelle partie")
        title.setObjectName("titleLabel")
        root.addWidget(title)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)

        self.pages.addWidget(self._build_step_players())
        self.pages.addWidget(self._build_step_themes())

        nav = QHBoxLayout()
        self.btn_cancel = QPushButton("Retour au menu")
        self.btn_cancel.clicked.connect(self._go_cancel)
        self.btn_prev = QPushButton("Précédent")
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next = QPushButton("Suivant")
        self.btn_next.setObjectName("menuButtonPrimary")
        self.btn_next.clicked.connect(self._go_next)
        nav.addWidget(self.btn_cancel)
        nav.addStretch()
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

    # ---------- Step 1: players ----------

    def _build_step_players(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Combien de joueurs ?"))

        count_row = QHBoxLayout()
        self.spin_players = QSpinBox()
        self.spin_players.setMinimum(MIN_PLAYERS)
        self.spin_players.setMaximum(9999)
        self.spin_players.setValue(MIN_PLAYERS)
        self.spin_players.valueChanged.connect(self._rebuild_player_fields)
        count_row.addWidget(self.spin_players)
        count_row.addStretch()
        layout.addLayout(count_row)

        layout.addWidget(QLabel("Noms des joueurs :"))
        self.players_container = QVBoxLayout()
        layout.addLayout(self.players_container)
        layout.addStretch()

        self._rebuild_player_fields(self.spin_players.value())
        return page

    def _rebuild_player_fields(self, count: int):
        current = len(self.player_name_edits)
        if count > current:
            for i in range(current, count):
                row = QHBoxLayout()
                label = QLabel(f"Joueur {i + 1} :")
                edit = QLineEdit()
                edit.setPlaceholderText(f"Joueur {i + 1}")
                row.addWidget(label)
                row.addWidget(edit)
                self.players_container.addLayout(row)
                self.player_name_edits.append(edit)
        elif count < current:
            for i in range(current - 1, count - 1, -1):
                edit = self.player_name_edits.pop(i)
                self._remove_row_containing(edit)

    def _remove_row_containing(self, edit: QLineEdit):
        for i in range(self.players_container.count() - 1, -1, -1):
            item = self.players_container.itemAt(i)
            row = item.layout()
            if row is None:
                continue
            for j in range(row.count()):
                w = row.itemAt(j).widget()
                if w is edit:
                    while row.count():
                        child = row.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()
                    self.players_container.takeAt(i)
                    return

    # ---------- Step 2: themes ----------

    def _build_step_themes(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"Choisissez exactement {REQUIRED_THEMES} thèmes pour cette partie :"))

        self.theme_list = QListWidget()
        self.theme_list.itemChanged.connect(self._on_theme_check_changed)
        layout.addWidget(self.theme_list, 1)

        self.lbl_theme_status = QLabel("")
        layout.addWidget(self.lbl_theme_status)
        return page

    def _refresh_theme_list(self):
        self.theme_list.blockSignals(True)
        self.theme_list.clear()
        for theme in self.db.list_themes():
            count = self.db.count_questions(theme.id)
            item = QListWidgetItem(f"{theme.name}  —  {count} question(s)")
            item.setData(Qt.UserRole, theme.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            if count == 0:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.theme_list.addItem(item)
        self.theme_list.blockSignals(False)
        self._update_theme_status()

    def _selected_theme_ids(self):
        ids = []
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        return ids

    def _on_theme_check_changed(self, changed_item):
        selected = self._selected_theme_ids()
        if len(selected) > REQUIRED_THEMES:
            changed_item.setCheckState(Qt.Unchecked)
            return
        self._update_theme_status()

    def _update_theme_status(self):
        selected = self._selected_theme_ids()
        low_count_names = []
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            theme_id = item.data(Qt.UserRole)
            if theme_id in selected and self.db.count_questions(theme_id) <= 2:
                low_count_names.append(item.text().split("  —")[0])
        msg = f"{len(selected)} / {REQUIRED_THEMES} thème(s) sélectionné(s)."
        if low_count_names:
            msg += "  ⚠️ Peu de questions pour : " + ", ".join(low_count_names)
        self.lbl_theme_status.setText(msg)

    # ---------- Navigation ----------

    def reset(self):
        self.spin_players.setValue(MIN_PLAYERS)
        self._rebuild_player_fields(MIN_PLAYERS)
        for edit in self.player_name_edits:
            edit.clear()
        self.pages.setCurrentIndex(0)
        self._update_nav_buttons()
        self._refresh_theme_list()

    def _update_nav_buttons(self):
        index = self.pages.currentIndex()
        self.btn_prev.setVisible(index > 0)
        self.btn_next.setText("Démarrer la partie" if index == self.pages.count() - 1 else "Suivant")

    def _go_cancel(self):
        self.main_window.sound.play("click")
        self.main_window.show_main_menu()

    def _go_prev(self):
        self.main_window.sound.play("click")
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))
        self._update_nav_buttons()

    def _go_next(self):
        self.main_window.sound.play("click")
        if self.pages.currentIndex() == 0:
            if not self._validate_players():
                return
            self.pages.setCurrentIndex(1)
            self._refresh_theme_list()
            self._update_nav_buttons()
        else:
            self._start_game()

    def _validate_players(self) -> bool:
        names = [e.text().strip() or e.placeholderText() for e in self.player_name_edits]
        if len(names) < MIN_PLAYERS:
            QMessageBox.warning(self, "Joueurs", f"Il faut au moins {MIN_PLAYERS} joueurs.")
            return False
        if len(set(names)) != len(names):
            QMessageBox.warning(self, "Joueurs", "Les noms des joueurs doivent être différents.")
            return False
        return True

    def _start_game(self):
        theme_ids = self._selected_theme_ids()
        if len(theme_ids) != REQUIRED_THEMES:
            QMessageBox.warning(self, "Thèmes", f"Sélectionnez exactement {REQUIRED_THEMES} thèmes.")
            return

        themes_by_id = {t.id: t for t in self.db.list_themes()}
        themes = [themes_by_id[tid] for tid in theme_ids]

        for theme in themes:
            if self.db.count_questions(theme.id) == 0:
                QMessageBox.warning(
                    self, "Thèmes", f"Le thème « {theme.name} » n'a aucune question, choisissez-en un autre."
                )
                return

        names = [e.text().strip() or e.placeholderText() for e in self.player_name_edits]
        players = [
            Player(name=name, color=self.db.next_player_color(i)) for i, name in enumerate(names)
        ]

        self.main_window.start_game(players, themes)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_nav_buttons()
