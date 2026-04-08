import os
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QTextEdit, QTreeWidgetItem, QTreeWidgetItemIterator, QProgressBar)
from PyQt6.QtCore import Qt

from gui.widgets import DragDropTreeWidget
from gui.workers import DownloadThread, ProcessingThread
from core.utils import AppUtils
from core.parser import GoProParser

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
        self.load_settings()

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
        # 💡 加上 self. 前綴，方便後續鎖定 UI
        self.btn_auto_sort = QPushButton("GoPro 自動分類 (依日期)")
        self.btn_auto_sort.clicked.connect(self.auto_categorize)
        self.btn_add_part = QPushButton("新增空白 Part")
        self.btn_add_part.clicked.connect(self.add_manual_part)
        self.btn_clear = QPushButton("清除清單")
        self.btn_clear.clicked.connect(self.tree.clear)
        list_btn_layout.addWidget(self.btn_auto_sort)
        list_btn_layout.addWidget(self.btn_add_part)
        list_btn_layout.addWidget(self.btn_clear)
        main_layout.addLayout(list_btn_layout)

        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("輸出資料夾: ❌ 尚未設定 (必填)")
        self.lbl_output.setStyleSheet("color: #ff5252; font-weight: bold;")
        # 💡 加上 self. 前綴
        self.btn_set_output = QPushButton("設定輸出位置")
        self.btn_set_output.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.lbl_output, stretch=1)
        output_layout.addWidget(self.btn_set_output)
        main_layout.addLayout(output_layout)

        self.btn_download = QPushButton("⚠️ 點此自動下載核心引擎 (FFmpeg / FFprobe)")
        self.btn_download.setObjectName("downloadBtn")
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setVisible(False)
        main_layout.addWidget(self.btn_download)

        action_layout = QHBoxLayout()
        self.btn_run = QPushButton("啟動功能 (開始合併)")
        self.btn_run.setObjectName("actionBtn")
        self.btn_run.clicked.connect(self.start_processing)
        
        self.btn_cancel = QPushButton("🛑 中斷任務")
        self.btn_cancel.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; font-size: 14px; padding: 8px; border-radius: 3px;")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)
        
        action_layout.addWidget(self.btn_run, stretch=3)
        action_layout.addWidget(self.btn_cancel, stretch=1)
        main_layout.addLayout(action_layout)

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

    def set_ui_locked(self, locked: bool):
        """💡 鎖定或解鎖 UI，防止在處理期間發生檔案異動"""
        self.btn_auto_sort.setEnabled(not locked)
        self.btn_add_part.setEnabled(not locked)
        self.btn_clear.setEnabled(not locked)
        self.btn_set_output.setEnabled(not locked)
        
        if locked:
            self.tree.setAcceptDrops(False)
            self.tree.setDragEnabled(False)
            self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        else:
            self.tree.setAcceptDrops(True)
            self.tree.setDragEnabled(True)
            self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def log(self, text, level="INFO"):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
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
            AppUtils.save_config({"last_output_folder": self.output_folder})

    def cancel_processing(self):
        if hasattr(self, 'process_thread') and self.process_thread.isRunning():
            reply = QMessageBox.question(self, '確認', '確定要強制中斷目前的合併任務嗎？', 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.btn_cancel.setEnabled(False)
                self.btn_cancel.setText("中斷中...")
                self.process_thread.cancel()

    def start_processing(self):
        if not self.output_folder:
            QMessageBox.warning(self, "操作錯誤", "請先設定「輸出資料夾」！")
            return

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
        
        if free_gb < (required_gb + 2):
            QMessageBox.critical(self, "硬碟空間不足", 
                               f"目標硬碟空間不足！\n\n需要：約 {required_gb:.2f} GB\n剩餘：{free_gb:.2f} GB\n\n請清理空間或更換輸出資料夾。")
            return

        # 💡 防呆機制：事前檢查是否有同名檔案即將被覆蓋
        existing_files = []
        for part_name in tree_data.keys():
            expected_mp4 = os.path.join(self.output_folder, f"{part_name}_merged.mp4")
            if os.path.exists(expected_mp4):
                existing_files.append(f"{part_name}_merged.mp4")
                
        if existing_files:
            msg = "以下檔案已存在於輸出資料夾，繼續執行將會直接覆蓋它們：\n\n"
            msg += "\n".join(existing_files[:5])
            if len(existing_files) > 5:
                msg += f"\n...等共 {len(existing_files)} 個檔案"
            msg += "\n\n確定要繼續並覆蓋舊檔案嗎？"
            
            reply = QMessageBox.warning(self, "覆蓋警告", msg, 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("處理中...")
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setText("🛑 中斷任務")
        
        # 💡 啟動時鎖住介面
        self.set_ui_locked(True)
        
        self.log(f"🚀 開始任務，預計總產出大小：{required_gb:.2f} GB")
        
        self.process_thread = ProcessingThread(tree_data, self.ffmpeg_path, self.output_folder)
        self.process_thread.log_signal.connect(self.log)
        self.process_thread.progress_signal.connect(self.update_progress)
        self.process_thread.finished_signal.connect(self.on_process_finished)
        self.process_thread.start()

    def on_process_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("啟動功能 (開始合併)")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setText("🛑 中斷任務")
        # 💡 任務結束或中斷時解鎖介面
        self.set_ui_locked(False)

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
        
        groups = GoProParser.group_files_by_date(all_files)

        for date_key, files in groups.items():
            part_item = QTreeWidgetItem([f"Part_{date_key}"])
            part_item.setExpanded(True)
            self.tree.addTopLevelItem(part_item)
            
            for file_path in files:
                child_item = QTreeWidgetItem([file_path])
                child_item.setFlags(child_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
                part_item.addChild(child_item)

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