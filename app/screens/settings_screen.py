from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SettingsScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = main_window.db

        root = QVBoxLayout(self)
        title = QLabel("Paramètres")
        title.setObjectName("titleLabel")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)

        self.chk_sound = QCheckBox("Activer les sons")
        form.addRow(self.chk_sound)

        vol_row = QHBoxLayout()
        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.lbl_volume = QLabel("80%")
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"{v}%"))
        vol_row.addWidget(self.slider_volume)
        vol_row.addWidget(self.lbl_volume)
        form.addRow("Volume :", vol_row)

        self.spin_wheel_duration = QDoubleSpinBox()
        self.spin_wheel_duration.setRange(1.0, 6.0)
        self.spin_wheel_duration.setSingleStep(0.5)
        self.spin_wheel_duration.setSuffix(" s")
        form.addRow("Durée de l'animation de la roue :", self.spin_wheel_duration)

        self.chk_avoid_repeats = QCheckBox("Éviter de reposer une question déjà posée pendant la partie")
        form.addRow(self.chk_avoid_repeats)

        self.chk_fullscreen = QCheckBox("Mode plein écran")
        form.addRow(self.chk_fullscreen)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Sombre", "Clair"])
        form.addRow("Thème visuel :", self.combo_theme)

        root.addLayout(form)
        root.addSpacing(20)

        btn_reset = QPushButton("Réinitialiser la banque de questions")
        btn_reset.setObjectName("menuButtonDanger")
        btn_reset.clicked.connect(self._reset_bank)
        root.addWidget(btn_reset)

        root.addStretch()

        buttons_row = QHBoxLayout()
        btn_back = QPushButton("Retour")
        btn_back.clicked.connect(self.main_window.show_main_menu)
        btn_save = QPushButton("Enregistrer")
        btn_save.setObjectName("menuButtonPrimary")
        btn_save.clicked.connect(self._save)
        buttons_row.addWidget(btn_back)
        buttons_row.addStretch()
        buttons_row.addWidget(btn_save)
        root.addLayout(buttons_row)

    def refresh(self):
        self.chk_sound.setChecked(self.db.get_setting("sound_enabled", "1") == "1")
        self.slider_volume.setValue(int(self.db.get_setting("volume", "80")))
        self.spin_wheel_duration.setValue(int(self.db.get_setting("wheel_duration_ms", "3000")) / 1000.0)
        self.chk_avoid_repeats.setChecked(self.db.get_setting("avoid_repeats", "1") == "1")
        self.chk_fullscreen.setChecked(self.db.get_setting("fullscreen", "0") == "1")
        self.combo_theme.setCurrentIndex(0 if self.db.get_setting("ui_theme", "dark") == "dark" else 1)

    def _save(self):
        self.db.set_setting("sound_enabled", "1" if self.chk_sound.isChecked() else "0")
        self.db.set_setting("volume", str(self.slider_volume.value()))
        self.db.set_setting("wheel_duration_ms", str(int(self.spin_wheel_duration.value() * 1000)))
        self.db.set_setting("avoid_repeats", "1" if self.chk_avoid_repeats.isChecked() else "0")
        self.db.set_setting("fullscreen", "1" if self.chk_fullscreen.isChecked() else "0")
        self.db.set_setting("ui_theme", "dark" if self.combo_theme.currentIndex() == 0 else "light")
        self.main_window.apply_settings()
        QMessageBox.information(self, "Paramètres", "Paramètres enregistrés.")

    def _reset_bank(self):
        reply = QMessageBox.warning(
            self,
            "Réinitialiser la banque de questions",
            "Ceci supprimera définitivement tous les thèmes et toutes les questions. Continuer ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.db.reset_question_bank()
            QMessageBox.information(self, "Banque de questions", "La banque de questions a été réinitialisée.")
