import os
import subprocess

class FFmpegRunner:
    def __init__(self, ffmpeg_path="ffmpeg.exe"):
        self.ffmpeg_path = ffmpeg_path

    def merge_videos(self, date_key, file_list, input_folder, output_folder=None):
        """
        使用 FFmpeg 的 concat demuxer 無損合併影片。
        """
        if not file_list:
            return False
            
        # 如果沒有指定輸出資料夾，就預設輸出到來源資料夾
        if not output_folder:
            output_folder = input_folder
            
        # 產生輸出檔名與路徑 (這會在自訂的輸出資料夾)
        output_filename = f"{date_key}_merged.mp4"
        output_path = os.path.join(output_folder, output_filename)
        
        # 建立 FFmpeg 需要的純文字清單檔 (必須放在輸入資料夾，這樣 file '檔名' 的相對路徑才有效)
        list_filename = f"concat_{date_key}.txt"
        list_path = os.path.join(input_folder, list_filename)
        
        try:
            with open(list_path, 'w', encoding='utf-8') as f:
                for video_file in file_list:
                    f.write(f"file '{video_file}'\n")
                    
            cmd = [
                self.ffmpeg_path,
                "-y",                 
                "-f", "concat",       
                "-safe", "0",         
                "-i", list_path,      
                "-c", "copy",         
                output_path           
            ]
            
            print(f"⚙️ 正在處理 {date_key} 的影片，共 {len(file_list)} 個檔案...")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                print(f"✅ {date_key} 合併完成！輸出檔案: {output_filename}")
                return True
            else:
                print(f"❌ {date_key} 合併失敗！錯誤: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"⚠️ 執行時發生例外錯誤: {e}")
            return False
            
        finally:
            if os.path.exists(list_path):
                os.remove(list_path)

# 簡單的本地測試區塊
if __name__ == "__main__":
    # 測試前請確保同一層目錄下有 ffmpeg.exe
    runner = FFmpegRunner("./ffmpeg.exe")
    # 如果你要單獨執行這個腳本測試，請把下面這行的註解拿掉，
    # 並換成你資料夾裡真的有的 GoPro 檔名與路徑
    # runner.merge_videos("2024-04-01", ["GX010001.MP4", "GX020001.MP4"], "你的測試資料夾路徑")