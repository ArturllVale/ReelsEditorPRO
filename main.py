import sys
import os
import subprocess
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow



def main():
    app = QApplication(sys.argv)
    
    # Carregar estilo QSS
    style_path = os.path.join(os.path.dirname(__file__), 'assets', 'style.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
            
    window = MainWindow()
    

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # Importante para multiprocessamento no Windows
    import multiprocessing
    multiprocessing.freeze_support()
    main()
