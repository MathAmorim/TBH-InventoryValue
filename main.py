import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from main_window import MainWindow

def setup_theme(app: QApplication) -> None:
    """Sets up the global Fusion dark palette theme."""
    app.setStyle('Fusion')
    palette = QPalette()
    
    # Backgrounds
    palette.setColor(QPalette.ColorRole.Window, QColor("#0b0b0b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e8e8e8"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111111"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#141414"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1d1d1d"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e8e8e8"))
    
    # Texts
    palette.setColor(QPalette.ColorRole.Text, QColor("#e8e8e8"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1d1d1d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e8e8e8"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#f2c94c"))
    
    # Accent colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#c8a24b"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0b0b0b"))
    
    # Disabled text states
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#7f8c8d"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#7f8c8d"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#7f8c8d"))
    
    app.setPalette(palette)

def main() -> None:
    app = QApplication(sys.argv)
    setup_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
