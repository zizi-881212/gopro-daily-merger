import sys
from PyQt6.QtWidgets import QApplication
from gui.app import GoProMergerApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 強制套用暗黑風格主題
    app.setStyle("Fusion")
    
    window = GoProMergerApp()
    window.show()
    sys.exit(app.exec())