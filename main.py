import tkinter as tk
from gui.app import GoProMergerApp

if __name__ == "__main__":
    root = tk.Tk()
    app = GoProMergerApp(root)
    # 在 Windows 下防止視窗模糊的小技巧 (可選)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    root.mainloop()