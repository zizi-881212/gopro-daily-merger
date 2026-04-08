import os

class ChapterBuilder:
    @staticmethod
    def build(chapters_info, out_dir, part_name):
        """
        產生 YouTube 資訊欄時間軸與 FFmpeg 內部封裝用的元數據檔
        chapters_info: list of (start_sec, duration, title)
        """
        yt_txt_path = os.path.join(out_dir, f"{part_name}_YT章節.txt")
        meta_txt_path = os.path.join(out_dir, f"{part_name}_meta.txt")
        
        try:
            with open(yt_txt_path, 'w', encoding='utf-8') as yt_f, open(meta_txt_path, 'w', encoding='utf-8') as meta_f:
                meta_f.write(";FFMETADATA1\n")
                for start_sec, dur, title in chapters_info:
                    # 格式化 YT 時間軸 (MM:SS 或 HH:MM:SS)
                    h = int(start_sec // 3600)
                    m = int((start_sec % 3600) // 60)
                    s = int(start_sec % 60)
                    time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    yt_f.write(f"{time_str} - {title}\n")
                    
                    # 寫入底層 Metadata 格式 (以毫秒為單位)
                    start_ms = int(start_sec * 1000)
                    end_ms = int((start_sec + dur) * 1000)
                    meta_f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start_ms}\nEND={end_ms}\ntitle={title}\n")
            
            # 回傳 (是否成功, 給UI顯示的檔名, meta檔的絕對路徑)
            return True, yt_txt_path, meta_txt_path
        except Exception as e:
            return False, str(e), None