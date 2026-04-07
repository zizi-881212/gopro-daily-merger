import os
import datetime
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QTextEdit, QTreeWidgetItem, QTreeWidgetItemIterator, QProgressBar)

from gui.widgets import DragDropTreeWidget
from gui.workers import DownloadThread, ProcessingThread
from core.utils import AppUtils

# 配置全域 Logging 系統
logging.basicConfig(
    filename='fishonjuice_merger.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)

class GoProMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro Daily Merger - FishOnJuice")
        self.resize(800, 800)
        
        self.current_dir = os.getcwd()
        self.ffmpeg_path = os.path.join(self.current_dir, "ffmpeg.exe")
        self.ffprobe_path = os.path.join(self.current_dir, "ffprobe.exe")
        self.output_folder = ""
        
        self.setup_dark_theme()
        self.setup_ui()
        self.check_dependencies()
        self.load_settings() # 讀取上次的設定

    def setup_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #e0e0e0; font-family: '微軟正黑體'; }
            QTreeWidget { background-color: #1e1e1e; alternate-background-color: #2a2a2a; color: #d4d4d4; border: 1px solid #3f3f3f; font-size: 13px; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #005A9E; color: white; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 6px; border-radius: 3px; font-family: '微軟正黑體'; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton#actionBtn { background-color: #0078D7; font-weight: bold; font-size: 14px; padding: 8px;}
            QPushButton#actionBtn:hover { background-color: #1084ea; }
            QPushButton#downloadBtn { background-color: #c62828; font-weight: bold; }
            QTextEdit { background-color: #1e1e1e; color: #4CAF50; font-family: 'Consolas'; border: 1px solid #3f3f3f;}
            QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #4CAF50; }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_layout = QVBoxLayout()
        title = QLabel("GoPro 影片佇列處理系統")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        brand = QLabel("Developed by FishOnJuice")
        brand.setStyleSheet("font-style: italic; color: #888;")
        header_layout.addWidget(title)
        header_layout.addWidget(brand)
        main_layout.addLayout(header_layout)

        self.tree = DragDropTreeWidget()
        main_layout.addWidget(self.tree, stretch=5)

        list_btn_layout = QHBoxLayout()
        btn_auto_sort = QPushButton("GoPro 自動分類 (依日期)")
        btn_auto_sort.clicked.connect(self.auto_categorize)
        btn_add_part = QPushButton("新增空白 Part")
        btn_add_part.clicked.connect(self.add_manual_part)
        btn_clear = QPushButton("清除清單")
        btn_clear.clicked.connect(self.tree.clear)
        list_btn_layout.addWidget(btn_auto_sort)
        list_btn_layout.addWidget(btn_add_part)
        list_btn_layout.addWidget(btn_clear)
        main_layout.addLayout(list_btn_layout)

        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("輸出資料夾: ❌ 尚未設定 (必填)")
        self.lbl_output.setStyleSheet("color: #ff5252; font-weight: bold;")
        btn_set_output = QPushButton("設定輸出位置")
        btn_set_output.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.lbl_output, stretch=1)
        output_layout.addWidget(btn_set_output)
        main_layout.addLayout(output_layout)

        self.btn_download = QPushButton("⚠️ 點此自動下載核心引擎 (FFmpeg / FFprobe)")
        self.btn_download.setObjectName("downloadBtn")
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setVisible(False)
        main_layout.addWidget(self.btn_download)

        self.btn_run = QPushButton("啟動功能 (開始合併)")
        self.btn_run.setObjectName("actionBtn")
        self.btn_run.clicked.connect(self.start_processing)
        main_layout.addWidget(self.btn_run)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_eta = QLabel("預估剩餘時間: --")
        progress_layout.addWidget(self.progress_bar, stretch=4)
        progress_layout.addWidget(self.lbl_eta, stretch=1)
        main_layout.addLayout(progress_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area, stretch=2)

    def log(self, text, level="INFO"):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        # 同步記錄到檔案
        if level == "INFO": logging.info(text.strip())
        elif level == "ERROR": logging.error(text.strip())

    def load_settings(self):
        config = AppUtils.load_config()
        last_folder = config.get("last_output_folder", "")
        if last_folder and os.path.exists(last_folder):
            self.output_folder = last_folder
            self.lbl_output.setText(f"輸出資料夾: {self.output_folder}")
            self.lbl_output.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self.output_folder = folder
            self.lbl_output.setText(f"輸出資料夾: {self.output_folder}")
            self.lbl_output.setStyleSheet("color: #4CAF50; font-weight: bold;")
            # 儲存設定
            AppUtils.save_config({"last_output_folder": self.output_folder})

    def start_processing(self):
        if not self.output_folder:
            QMessageBox.warning(self, "操作錯誤", "請先設定「輸出資料夾」！")
            return

        # --- 磁碟空間預檢 ---
        total_size_bytes = 0
        tree_data = {}
        for i in range(self.tree.topLevelItemCount()):
            part_item = self.tree.topLevelItem(i)
            files = []
            for j in range(part_item.childCount()):
                f_path = part_item.child(j).text(0)
                files.append(f_path)
                total_size_bytes += os.path.getsize(f_path)
            if files: tree_data[part_item.text(0)] = files

        if not tree_data:
            self.log("⚠️ 清單中沒有可處理的檔案。")
            return

        free_gb = AppUtils.get_free_space_gb(self.output_folder)
        required_gb = total_size_bytes / (1024**3)
        
        # 預留 2GB 安全空間
        if free_gb < (required_gb + 2):
            QMessageBox.critical(self, "硬碟空間不足", 
                               f"目標硬碟空間不足！\n\n需要：約 {required_gb:.2f} GB\n剩餘：{free_gb:.2f} GB\n\n請清理空間或更換輸出資料夾。")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("處理中...")
        self.log(f"🚀 開始合併任務，預計總產出大小：{required_gb:.2f} GB")
        
        self.process_thread = ProcessingThread(tree_data, self.ffmpeg_path, self.output_folder)
        self.process_thread.log_signal.connect(self.log)
        self.process_thread.progress_signal.connect(self.update_progress)
        self.process_thread.finished_signal.connect(self.on_process_finished)
        self.process_thread.start()

    # (其餘 check_dependencies, start_download, closeEvent 等保持不變...)
    def on_process_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("啟動功能 (開始合併)")

    def update_progress(self, percent, eta_str):
        self.progress_bar.setValue(percent)
        self.lbl_eta.setText(f"預計剩餘: {eta_str}")

    def check_dependencies(self):
        if os.path.exists(self.ffmpeg_path) and os.path.exists(self.ffprobe_path):
            self.btn_download.setVisible(False)
            self.btn_run.setEnabled(True)
            self.btn_run.setText("啟動功能 (開始合併)")
            self.log("✅ 系統環境檢查完畢，核心引擎已就緒。")
        else:
            self.btn_download.setVisible(True)
            self.btn_run.setEnabled(False)
            self.btn_run.setText("請先安裝核心引擎")
            self.log("⚠️ 偵測不到核心引擎，請點擊上方按鈕下載。")

    def start_download(self):
        self.btn_download.setEnabled(False)
        self.btn_download.setText("⏳ 下載與安裝中...")
        self.log_area.clear()
        self.dl_thread = DownloadThread(self.current_dir)
        self.dl_thread.log_signal.connect(self.log)
        self.dl_thread.finished_signal.connect(self.on_download_finished)
        self.dl_thread.start()

    def on_download_finished(self, success):
        if success: self.check_dependencies()
        else:
            self.btn_download.setEnabled(True)
            self.btn_download.setText("⚠️ 下載失敗，點此重試")

    def add_manual_part(self):
        part_item = QTreeWidgetItem([f"Part_{datetime.datetime.now().strftime('%H%M%S')}"])
        part_item.setExpanded(True)
        self.tree.addTopLevelItem(part_item)

    def auto_categorize(self):
        all_files = []
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            path = item.text(0)
            if path.upper().endswith(('.MP4', '.JPG', '.JPEG', '.PNG')) and os.path.isfile(path):
                all_files.append(path)
            iterator += 1
            
        if not all_files:
            QMessageBox.warning(self, "提示", "請先將檔案拖曳至清單中。")
            return

        self.tree.clear()
        groups = {}
        for file_path in all_files:
            filename = os.path.basename(file_path)
            if filename.upper().startswith('GX') or filename.upper().endswith(('.JPG', '.PNG', '.JPEG')):
                mtime = os.path.getmtime(file_path)
                date_key = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                groups.setdefault(date_key, []).append(file_path)
            else:
                groups.setdefault('未分類', []).append(file_path)

        for date_key, files in groups.items():
            part_item = QTreeWidgetItem([f"Part_{date_key}"])
            part_item.setExpanded(True)
            self.tree.addTopLevelItem(part_item)
            
            # 🐛 修正排序 Bug：統一回傳 (優先權, 排序條件1, 排序條件2) 避免 Tuple 與 Float 互相比較
            files.sort(
                key=lambda x: (0, os.path.basename(x)[4:8], os.path.basename(x)[2:4]) 
                if (os.path.basename(x).upper().startswith('GX') and len(os.path.basename(x)) >= 12) 
                else (1, os.path.getmtime(x), os.path.basename(x))
            )
            
            for file_path in files:
                part_item.addChild(QTreeWidgetItem([file_path]))

    def closeEvent(self, event):
        is_processing = hasattr(self, 'process_thread') and self.process_thread.isRunning()
        if is_processing:
            reply = QMessageBox.question(self, '警告', '正在合併影片中，確定要中斷並退出？', 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.process_thread.cancel()
                self.process_thread.wait(2000)
                event.accept()
            else: event.ignore()
        else: event.accept()