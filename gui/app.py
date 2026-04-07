import os
import datetime
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, 
                             QFileDialog, QMessageBox, QTextEdit, QAbstractItemView,
                             QMenu, QInputDialog, QTreeWidgetItemIterator)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.ffmpeg_runner import FFmpegRunner
from core.downloader import FFmpegDownloader


class ProcessingThread(QThread):
    """將合併運算獨立到背景執行緒，保護 UI 不卡死"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, tree_data, ffmpeg_path, output_folder):
        super().__init__()
        self.tree_data = tree_data
        self.ffmpeg_path = ffmpeg_path
        self.output_folder = output_folder

    def run(self):
        runner = FFmpegRunner(self.ffmpeg_path)
        
        for part_name, files in self.tree_data.items():
            self.log_signal.emit(f"\n⏳ 正在準備 {part_name} 的素材...")
            
            ref_video = next((f for f in files if f.upper().endswith('.MP4')), None)
            if not ref_video:
                self.log_signal.emit(f"❌ {part_name} 內無影片檔，無法作為轉檔範本，跳過此 Part。")
                continue
                
            ref_info = runner.get_video_info(ref_video)
            processed_files = []
            temp_files = []
            
            for f in files:
                if f.upper().endswith(('.JPG', '.PNG', '.JPEG')):
                    self.log_signal.emit(f"📸 轉換照片中 (3秒): {os.path.basename(f)}")
                    temp_v = runner.convert_image_to_video(f, ref_info, duration=3)
                    processed_files.append(temp_v)
                    temp_files.append(temp_v)
                else:
                    processed_files.append(f)
                    
            self.log_signal.emit(f"⚙️ 正在合併 {part_name} (共 {len(processed_files)} 個檔案)...")
            
            # 若無自訂輸出資料夾，預設儲存於第一個檔案的所在位置
            out_dir = self.output_folder if self.output_folder else os.path.dirname(files[0])
            success = runner.merge_videos(part_name, processed_files, out_dir)
            
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
                    
            if success:
                self.log_signal.emit(f"✅ {part_name} 合併完成！")
            else:
                self.log_signal.emit(f"❌ {part_name} 合併失敗。")
                
        self.log_signal.emit("\n🎉 所有任務處理完畢！")
        self.finished_signal.emit()


class DragDropTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["檔案路徑 / 分組 (Part)"])
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.valid_exts = ('.MP4', '.JPG', '.JPEG', '.PNG')

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item: return

        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #2b2b2b; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #005A9E; }")
        
        is_part = item.parent() is None

        if is_part:
            rename_action = menu.addAction("✏️ 重新命名 Part")
            delete_action = menu.addAction("🗑️ 移除此 Part (包含底下檔案)")
            action = menu.exec(self.viewport().mapToGlobal(position))
            
            if action == rename_action:
                new_name, ok = QInputDialog.getText(self, "重新命名 Part", "請輸入新的名稱:", text=item.text(0))
                if ok and new_name.strip(): item.setText(0, new_name.strip())
            elif action == delete_action:
                self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
            open_folder_action = menu.addAction("📂 開啟檔案所在位置")
            remove_file_action = menu.addAction("❌ 從清單移除")
            action = menu.exec(self.viewport().mapToGlobal(position))
            
            if action == open_folder_action:
                subprocess.Popen(f'explorer /select,"{item.text(0)}"')
            elif action == remove_file_action:
                item.parent().removeChild(item)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path) and path.upper().endswith(self.valid_exts):
                    self.addTopLevelItem(QTreeWidgetItem([path]))
                elif os.path.isdir(path):
                    for f in os.listdir(path):
                        if f.upper().endswith(self.valid_exts):
                            self.addTopLevelItem(QTreeWidgetItem([os.path.normpath(os.path.join(path, f))]))
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class GoProMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro Daily Merger - FishOnJuice")
        self.resize(800, 700)
        self.current_dir = os.getcwd()
        self.ffmpeg_path = os.path.join(self.current_dir, "ffmpeg.exe")
        self.output_folder = ""
        self.setup_dark_theme()
        self.setup_ui()

    def setup_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #e0e0e0; font-family: '微軟正黑體'; }
            QTreeWidget { background-color: #1e1e1e; alternate-background-color: #2a2a2a; color: #d4d4d4; border: 1px solid #3f3f3f; font-size: 13px; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #005A9E; color: white; }
            QPushButton { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 6px; border-radius: 3px; font-family: '微軟正黑體'; }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton#actionBtn { background-color: #0078D7; font-weight: bold; }
            QPushButton#actionBtn:hover { background-color: #1084ea; }
            QTextEdit { background-color: #1e1e1e; color: #4CAF50; font-family: 'Consolas'; border: 1px solid #3f3f3f;}
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
        self.lbl_output = QLabel("輸出資料夾: (預設為原始檔同目錄)")
        btn_set_output = QPushButton("更改輸出位置")
        btn_set_output.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.lbl_output, stretch=1)
        output_layout.addWidget(btn_set_output)
        main_layout.addLayout(output_layout)

        self.btn_run = QPushButton("啟動功能 (開始合併)")
        self.btn_run.setObjectName("actionBtn")
        self.btn_run.clicked.connect(self.start_processing)
        main_layout.addWidget(self.btn_run)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area, stretch=2)

    def log(self, text):
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self.output_folder = folder
            self.lbl_output.setText(f"輸出資料夾: {self.output_folder}")

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
            if date_key != '未分類':
                files.sort(key=lambda x: (os.path.basename(x)[4:8], os.path.basename(x)[2:4]) if os.path.basename(x).upper().endswith('.MP4') and len(os.path.basename(x)) >= 12 else (x, ""))
            
            part_item = QTreeWidgetItem([f"Part_{date_key}"])
            part_item.setExpanded(True)
            self.tree.addTopLevelItem(part_item)
            for file_path in files:
                part_item.addChild(QTreeWidgetItem([file_path]))

    def start_processing(self):
        self.btn_run.setEnabled(False)
        if not os.path.exists(self.ffmpeg_path):
            if QMessageBox.askyesno("缺少核心組件", "是否由 FishOnJuice 自動下載 FFmpeg 與 FFprobe？"):
                self.log("🌐 準備下載核心引擎...")
                import threading
                threading.Thread(target=self.download_and_then_process, daemon=True).start()
            else:
                self.btn_run.setEnabled(True)
            return
            
        tree_data = {}
        for i in range(self.tree.topLevelItemCount()):
            part_item = self.tree.topLevelItem(i)
            files = [part_item.child(j).text(0) for j in range(part_item.childCount())]
            if files: tree_data[part_item.text(0)] = files

        if not tree_data:
            self.log("⚠️ 清單中沒有可處理的檔案。")
            self.btn_run.setEnabled(True)
            return

        self.log("🚀 開始處理佇列...")
        self.thread = ProcessingThread(tree_data, self.ffmpeg_path, self.output_folder)
        self.thread.log_signal.connect(self.log)
        self.thread.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.thread.start()

    def download_and_then_process(self):
        downloader = FFmpegDownloader()
        def log_callback(msg): self.log(msg)
        if downloader.download_and_extract(self.current_dir, log_callback):
            self.start_processing()
        else:
            self.btn_run.setEnabled(True)