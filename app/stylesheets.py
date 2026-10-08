BASE_STYLE = """
QLabel#titleLabel { font-size: 30px; font-weight: bold; }
QLabel#subtitleLabel { font-size: 16px; }
QLabel#playerTurnLabel { font-size: 26px; font-weight: bold; }
QLabel#instructionLabel { font-size: 15px; font-style: italic; }
QLabel#themeNameLabel { font-size: 20px; }
QLabel#questionLabel { font-size: 22px; }
QLabel#answerLabel { font-size: 20px; font-weight: bold; }
QLabel#shotLabel { font-size: 22px; font-weight: bold; }
QLabel#winnerLabel { font-size: 30px; font-weight: bold; }
QPushButton#menuButton { font-size: 16px; border-radius: 10px; padding: 10px; }
QPushButton#menuButtonPrimary { font-size: 15px; font-weight: bold; border-radius: 8px; padding: 8px 16px; background-color: #3d8bfd; color: white; }
QPushButton#menuButtonDanger { font-size: 15px; border-radius: 8px; padding: 8px 16px; background-color: #d9534f; color: white; }
QFrame#playerRow { border-radius: 8px; padding: 6px; }
QFrame#playerRow[active="true"] { border: 2px solid #f1c40f; }
QFrame#playerRow[active="false"] { border: 2px solid transparent; }
"""

DARK_STYLE = (
    """
    QWidget { background-color: #1e1f26; color: #eaeaea; }
    QPushButton { background-color: #2c2e3a; color: #eaeaea; border: 1px solid #3a3d4d; padding: 6px; border-radius: 6px; }
    QPushButton:hover { background-color: #3a3d4d; }
    QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget {
        background-color: #2a2b35; color: #eaeaea; border: 1px solid #3a3d4d; border-radius: 4px;
    }
    QFrame#playerRow { background-color: #2a2b35; }
    """
    + BASE_STYLE
)

LIGHT_STYLE = (
    """
    QWidget { background-color: #f5f6fa; color: #202020; }
    QPushButton { background-color: #ffffff; color: #202020; border: 1px solid #cccccc; padding: 6px; border-radius: 6px; }
    QPushButton:hover { background-color: #eaeaea; }
    QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTableWidget {
        background-color: #ffffff; color: #202020; border: 1px solid #cccccc; border-radius: 4px;
    }
    QFrame#playerRow { background-color: #ffffff; }
    """
    + BASE_STYLE
)
