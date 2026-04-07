import os
import urllib.request
import zipfile
import tempfile
import shutil

class FFmpegDownloader:
    def __init__(self):
        # 這是 BtbN 維護的 Windows 版 FFmpeg 最新發佈版直連網址
        self.download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
    def download_and_extract(self, target_dir, log_callback=None):
        """下載 FFmpeg 壓縮檔並只抽出 ffmpeg.exe 放進目標資料夾"""
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        temp_zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg_temp.zip")
        
        try:
            log("⬇️ 開始下載 FFmpeg (檔案約 100MB，請稍候)...")
            
            # 建立一個簡單的 Request 物件，模擬瀏覽器行為避免被擋
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            log("📦 下載完成，正在解壓縮並安裝...")
            
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # 尋找壓縮檔內的 ffmpeg.exe
                exe_path_in_zip = None
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("ffmpeg.exe"):
                        exe_path_in_zip = file_info.filename
                        break
                        
                if exe_path_in_zip:
                    # 抽出到暫存區，再移動並重新命名到我們的專案目錄
                    extracted_path = zip_ref.extract(exe_path_in_zip, tempfile.gettempdir())
                    final_exe_path = os.path.join(target_dir, "ffmpeg.exe")
                    shutil.move(extracted_path, final_exe_path)
                    log("✨ FFmpeg 核心引擎安裝成功！")
                    return True
                else:
                    log("❌ 壓縮檔內找不到 ffmpeg.exe")
                    return False
                    
        except Exception as e:
            log(f"⚠️ 下載或安裝過程發生錯誤: {e}")
            return False
            
        finally:
            # 養成好習慣：清理暫存垃圾
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)

# 簡單的本地測試區塊
if __name__ == "__main__":
    dl = FFmpegDownloader()
    dl.download_and_extract(os.getcwd())