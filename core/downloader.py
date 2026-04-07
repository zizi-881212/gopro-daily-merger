import os
import urllib.request
import zipfile
import tempfile
import shutil

class FFmpegDownloader:
    def __init__(self):
        self.download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
    def download_and_extract(self, target_dir, log_callback=None):
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        temp_zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg_temp.zip")
        
        try:
            log("⬇️ 開始下載 FFmpeg 與 FFprobe (檔案較大，請稍候)...")
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            log("📦 下載完成，正在解壓縮並安裝...")
            
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                ffmpeg_extracted = False
                ffprobe_extracted = False
                
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("ffmpeg.exe"):
                        extracted_path = zip_ref.extract(file_info.filename, tempfile.gettempdir())
                        shutil.move(extracted_path, os.path.join(target_dir, "ffmpeg.exe"))
                        ffmpeg_extracted = True
                    elif file_info.filename.endswith("ffprobe.exe"):
                        extracted_path = zip_ref.extract(file_info.filename, tempfile.gettempdir())
                        shutil.move(extracted_path, os.path.join(target_dir, "ffprobe.exe"))
                        ffprobe_extracted = True
                        
                if ffmpeg_extracted and ffprobe_extracted:
                    log("✨ FFmpeg 雙核心引擎安裝成功！")
                    return True
                else:
                    log("❌ 壓縮檔內找不到必要的執行檔。")
                    return False
                    
        except Exception as e:
            log(f"⚠️ 下載或安裝發生錯誤: {e}")
            return False
        finally:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)