from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .excel_import_dialog import ExcelImportDialog


def _color_icon(color: str) -> QIcon:
    pix = QPixmap(16, 16)
    pix.fill(QColor(color))
    return QIcon(pix)


class QuestionEditDialog(QDialog):
    def __init__(self, parent=None, question_text: str = "", answer_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Question")
        self.resize(480, 320)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Question :"))
        self.edit_question = QPlainTextEdit(question_text)
        layout.addWidget(self.edit_question)

        layout.addWidget(QLabel("Réponse :"))
        self.edit_answer = QPlainTextEdit(answer_text)
        layout.addWidget(self.edit_answer)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.edit_question.toPlainText().strip() or not self.edit_answer.toPlainText().strip():
            QMessageBox.warning(self, "Champs manquants", "La question et la réponse sont obligatoires.")
            return
        self.accept()

    def values(self):
        return self.edit_question.toPlainText().strip(), self.edit_answer.toPlainText().strip()


class QuestionsManagerScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = main_window.db
        self.current_theme_id = None

        root = QVBoxLayout(self)
        title = QLabel("Banque de questions")
        title.setObjectName("titleLabel")
        root.addWidget(title)

        body = QHBoxLayout()
        root.addLayout(body, 1)

        left = QVBoxLayout()
        left.addWidget(QLabel("Thèmes"))
        self.theme_list = QListWidget()
        self.theme_list.currentItemChanged.connect(self._on_theme_selected)
        left.addWidget(self.theme_list, 1)

        theme_buttons = QHBoxLayout()
        btn_add_theme = QPushButton("Ajouter")
        btn_add_theme.clicked.connect(self._add_theme)
        btn_rename_theme = QPushButton("Renommer")
        btn_rename_theme.clicked.connect(self._rename_theme)
        btn_color_theme = QPushButton("Couleur")
        btn_color_theme.clicked.connect(self._recolor_theme)
        btn_delete_theme = QPushButton("Supprimer")
        btn_delete_theme.clicked.connect(self._delete_theme)
        for b in (btn_add_theme, btn_rename_theme, btn_color_theme, btn_delete_theme):
            theme_buttons.addWidget(b)
        left.addLayout(theme_buttons)

        body.addLayout(left, 1)

        right = QVBoxLayout()
        self.lbl_theme = QLabel("Sélectionnez un thème")
        self.lbl_theme.setObjectName("subtitleLabel")
        right.addWidget(self.lbl_theme)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Question", "Réponse"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_question)
        right.addWidget(self.table, 1)

        q_buttons = QHBoxLayout()
        btn_add_q = QPushButton("Ajouter une question")
        btn_add_q.clicked.connect(self._add_question)
        btn_edit_q = QPushButton("Éditer")
        btn_edit_q.clicked.connect(self._edit_question)
        btn_delete_q = QPushButton("Supprimer")
        btn_delete_q.clicked.connect(self._delete_question)
        btn_import = QPushButton("Importer depuis Excel…")
        btn_import.setObjectName("menuButtonPrimary")
        btn_import.clicked.connect(self._import_excel)
        for b in (btn_add_q, btn_edit_q, btn_delete_q, btn_import):
            q_buttons.addWidget(b)
        right.addLayout(q_buttons)

        body.addLayout(right, 2)

        bottom = QHBoxLayout()
        btn_back = QPushButton("Retour au menu")
        btn_back.clicked.connect(self.main_window.show_main_menu)
        bottom.addWidget(btn_back)
        bottom.addStretch()
        root.addLayout(bottom)

    def refresh(self):
        self.theme_list.blockSignals(True)
        selected_id = self.current_theme_id
        self.theme_list.clear()
        for theme in self.db.list_themes():
            count = self.db.count_questions(theme.id)
            item = QListWidgetItem(_color_icon(theme.color), f"{theme.name}  ({count})")
            item.setData(Qt.UserRole, theme.id)
            self.theme_list.addItem(item)
            if theme.id == selected_id:
                self.theme_list.setCurrentItem(item)
        self.theme_list.blockSignals(False)
        if self.theme_list.currentItem() is None and self.theme_list.count() > 0:
            self.theme_list.setCurrentRow(0)
        elif self.theme_list.count() == 0:
            self.current_theme_id = None
            self.lbl_theme.setText("Sélectionnez un thème")
            self.table.setRowCount(0)
        else:
            self._reload_questions()

    def _on_theme_selected(self, current, previous):
        if current is None:
            self.current_theme_id = None
            self.table.setRowCount(0)
            self.lbl_theme.setText("Sélectionnez un thème")
            return
        self.current_theme_id = current.data(Qt.UserRole)
        self._reload_questions()

    def _reload_questions(self):
        if self.current_theme_id is None:
            return
        themes = {t.id: t for t in self.db.list_themes()}
        theme = themes.get(self.current_theme_id)
        if theme is None:
            return
        self.lbl_theme.setText(f"Thème : {theme.name}")
        questions = self.db.list_questions(self.current_theme_id)
        self.table.setRowCount(len(questions))
        for row, q in enumerate(questions):
            item_q = QTableWidgetItem(q.question)
            item_q.setData(Qt.UserRole, q.id)
            self.table.setItem(row, 0, item_q)
            self.table.setItem(row, 1, QTableWidgetItem(q.answer))

    # ---------- Theme actions ----------

    def _add_theme(self):
        name, ok = QInputDialog.getText(self, "Nouveau thème", "Nom du thème :")
        if not ok or not name.strip():
            return
        try:
            self.db.add_theme(name)
        except Exception:
            QMessageBox.warning(self, "Thème existant", "Ce thème existe déjà.")
            return
        self.refresh()

    def _rename_theme(self):
        if self.current_theme_id is None:
            return
        themes = {t.id: t for t in self.db.list_themes()}
        theme = themes[self.current_theme_id]
        name, ok = QInputDialog.getText(self, "Renommer le thème", "Nouveau nom :", text=theme.name)
        if not ok or not name.strip():
            return
        self.db.rename_theme(self.current_theme_id, name)
        self.refresh()

    def _recolor_theme(self):
        if self.current_theme_id is None:
            return
        themes = {t.id: t for t in self.db.list_themes()}
        theme = themes[self.current_theme_id]
        color = QColorDialog.getColor(QColor(theme.color), self, "Couleur du thème")
        if color.isValid():
            self.db.set_theme_color(self.current_theme_id, color.name())
            self.refresh()

    def _delete_theme(self):
        if self.current_theme_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Supprimer le thème",
            "Supprimer ce thème et toutes ses questions ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db.delete_theme(self.current_theme_id)
            self.current_theme_id = None
            self.refresh()

    # ---------- Question actions ----------

    def _add_question(self):
        if self.current_theme_id is None:
            QMessageBox.information(self, "Aucun thème", "Créez ou sélectionnez d'abord un thème.")
            return
        dlg = QuestionEditDialog(self)
        if dlg.exec() == QDialog.Accepted:
            q, a = dlg.values()
            self.db.add_question(self.current_theme_id, q, a)
            self.refresh()

    def _selected_question_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _edit_question(self):
        q_id = self._selected_question_id()
        if q_id is None:
            return
        row = self.table.currentRow()
        current_q = self.table.item(row, 0).text()
        current_a = self.table.item(row, 1).text()
        dlg = QuestionEditDialog(self, current_q, current_a)
        if dlg.exec() == QDialog.Accepted:
            q, a = dlg.values()
            self.db.update_question(q_id, q, a)
            self.refresh()

    def _delete_question(self):
        q_id = self._selected_question_id()
        if q_id is None:
            return
        self.db.delete_question(q_id)
        self.refresh()

    def _import_excel(self):
        dlg = ExcelImportDialog(self.db, self)
        dlg.exec()
        self.refresh()
