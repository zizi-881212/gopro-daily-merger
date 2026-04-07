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
        
        # ==========================================
        # 階段一：全局掃雷 (Global Pre-flight Check)
        # ==========================================
        self.log_signal.emit("\n🔎 正在進行全局素材掃雷與規格檢查...")
        self.progress_signal.emit(0, "掃雷中...")
        
        for part_name, files in self.tree_data.items():
            if self.is_cancelled: return
            
            ref_video = next((f for f in files if f.upper().endswith('.MP4')), None)
            if not ref_video:
                self.log_signal.emit(f"⚠️ {part_name} 內無影片檔，將在合併時跳過此 Part。")
                continue
                
            ref_info = self.runner.get_video_info(ref_video)
            is_compatible, error_msg = self.runner.verify_video_compatibility(files, ref_info)
            
            if not is_compatible:
                self.log_signal.emit(f"❌ 掃雷失敗！在 {part_name} 發現致命問題：\n   原因：{error_msg}")
                self.log_signal.emit("🛑 為保護資料安全，已阻擋本次合併任務。請於清單中移除異常檔案後再試。")
                self.progress_signal.emit(0, "任務已阻擋")
                self.finished_signal.emit()
                return # 只要全域發現任何一顆地雷，整個任務直接打回票！
                
        if self.is_cancelled: return
        self.log_signal.emit("✅ 全局掃雷通過！所有素材皆安全無虞，準備開始正式處理。\n" + "-"*40)
        
        # ==========================================
        # 階段二：正式處理與合併
        # ==========================================
        for part_name, files in self.tree_data.items():
            if self.is_cancelled: break
            
            self.log_signal.emit(f"\n⏳ 正在準備 {part_name} 的素材...")
            
            ref_video = next((f for f in files if f.upper().endswith('.MP4')), None)
            if not ref_video: continue
            ref_info = self.runner.get_video_info(ref_video)
            
            processed_files = []
            temp_files = []
            total_duration = 0.0
            chapters_info = [] 
            
            for f in files:
                if self.is_cancelled: break
                
                filename = os.path.basename(f)
                if f.upper().endswith(('.JPG', '.PNG', '.JPEG')):
                    self.log_signal.emit(f"📸 轉換照片中 (3秒): {filename}")
                    temp_v = self.runner.convert_image_to_video(f, ref_info, duration=3)
                    processed_files.append(temp_v)
                    temp_files.append(temp_v)
                    chapters_info.append((total_duration, 3.0, filename))
                    total_duration += 3.0
                else:
                    processed_files.append(f)
                    dur = self.runner.get_video_duration(f)
                    chapters_info.append((total_duration, dur, filename))
                    total_duration += dur
                    
            if self.is_cancelled: break
            
            out_dir = self.output_folder if self.output_folder else os.path.dirname(files[0])
            yt_txt_path = os.path.join(out_dir, f"{part_name}_YT章節.txt")
            meta_txt_path = os.path.join(out_dir, f"{part_name}_meta.txt")
            temp_files.append(meta_txt_path) 
            
            try:
                with open(yt_txt_path, 'w', encoding='utf-8') as yt_f, open(meta_txt_path, 'w', encoding='utf-8') as meta_f:
                    meta_f.write(";FFMETADATA1\n")
                    for start_sec, dur, title in chapters_info:
                        h = int(start_sec // 3600)
                        m = int((start_sec % 3600) // 60)
                        s = int(start_sec % 60)
                        time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                        yt_f.write(f"{time_str} - {title}\n")
                        
                        start_ms = int(start_sec * 1000)
                        end_ms = int((start_sec + dur) * 1000)
                        meta_f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={title}\n")
                self.log_signal.emit(f"📝 已產生 YouTube 資訊欄時間軸：{os.path.basename(yt_txt_path)}")
            except Exception as e:
                self.log_signal.emit(f"⚠️ 產生章節資訊時發生錯誤: {e}")

            self.log_signal.emit(f"⚙️ 正在合併 {part_name} (總時長約 {int(total_duration)} 秒)...")
            
            def progress_cb(percent, eta):
                eta_str = f"{int(eta)} 秒" if eta < 60 else f"{int(eta//60)} 分 {int(eta%60)} 秒"
                self.progress_signal.emit(percent, eta_str)
            
            success, err_msg = self.runner.merge_videos(part_name, processed_files, out_dir, total_duration, progress_cb, metadata_path=meta_txt_path)
            
            if not self.is_cancelled:
                self.progress_signal.emit(100, "完成")
            
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
                    
            if success and not self.is_cancelled:
                self.log_signal.emit(f"✅ {part_name} 合併完成！")
            elif not self.is_cancelled:
                self.log_signal.emit(f"❌ {part_name} 合併失敗。\n   詳細原因：{err_msg}")
                
        if self.is_cancelled:
            self.log_signal.emit("\n🛑 任務已由使用者強制中斷！")
        else:
            self.log_signal.emit("\n🎉 所有任務處理完畢！")
            
        self.progress_signal.emit(100, "--")
        self.finished_signal.emit()