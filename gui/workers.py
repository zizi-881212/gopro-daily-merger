import os
from PyQt6.QtCore import QThread, pyqtSignal
from core.ffmpeg_runner import FFmpegRunner
from core.downloader import FFmpegDownloader

class DownloadThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, target_dir):
        super().__init__()
        self.target_dir = target_dir

    def run(self):
        downloader = FFmpegDownloader()
        success = downloader.download_and_extract(self.target_dir, lambda msg: self.log_signal.emit(msg))
        self.finished_signal.emit(success)

class ProcessingThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()

    def __init__(self, tree_data, ffmpeg_path, output_folder):
        super().__init__()
        self.tree_data = tree_data
        self.ffmpeg_path = ffmpeg_path
        self.output_folder = output_folder
        self.is_cancelled = False
        self.runner = None

    def cancel(self):
        """接收外部中斷訊號，並轉傳給底層的 FFmpegRunner"""
        self.is_cancelled = True
        if self.runner:
            self.runner.cancel()

    def run(self):
        self.runner = FFmpegRunner(self.ffmpeg_path)
        
        for part_name, files in self.tree_data.items():
            if self.is_cancelled: break
            
            self.log_signal.emit(f"\n⏳ 正在準備 {part_name} 的素材...")
            self.progress_signal.emit(0, "計算中...")
            
            ref_video = next((f for f in files if f.upper().endswith('.MP4')), None)
            if not ref_video:
                self.log_signal.emit(f"❌ {part_name} 內無影片檔，無法作為轉檔範本，跳過此 Part。")
                continue
                
            ref_info = self.runner.get_video_info(ref_video)
            processed_files = []
            temp_files = []
            total_duration = 0.0
            
            for f in files:
                if self.is_cancelled: break
                
                if f.upper().endswith(('.JPG', '.PNG', '.JPEG')):
                    self.log_signal.emit(f"📸 轉換照片中 (3秒): {os.path.basename(f)}")
                    temp_v = self.runner.convert_image_to_video(f, ref_info, duration=3)
                    processed_files.append(temp_v)
                    temp_files.append(temp_v)
                    total_duration += 3.0
                else:
                    processed_files.append(f)
                    total_duration += self.runner.get_video_duration(f)
                    
            if self.is_cancelled: break
            
            self.log_signal.emit(f"⚙️ 正在合併 {part_name} (總時長約 {int(total_duration)} 秒)...")
            out_dir = self.output_folder if self.output_folder else os.path.dirname(files[0])
            
            def progress_cb(percent, eta):
                eta_str = f"{int(eta)} 秒" if eta < 60 else f"{int(eta//60)} 分 {int(eta%60)} 秒"
                self.progress_signal.emit(percent, eta_str)
            
            success = self.runner.merge_videos(part_name, processed_files, out_dir, total_duration, progress_cb)
            
            if not self.is_cancelled:
                self.progress_signal.emit(100, "完成")
            
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
                    
            if success and not self.is_cancelled:
                self.log_signal.emit(f"✅ {part_name} 合併完成！")
            elif not self.is_cancelled:
                self.log_signal.emit(f"❌ {part_name} 合併失敗。")
                
        if self.is_cancelled:
            self.log_signal.emit("\n🛑 任務已強制中斷！")
        else:
            self.log_signal.emit("\n🎉 所有任務處理完畢！")
            
        self.progress_signal.emit(100, "--")
        self.finished_signal.emit()