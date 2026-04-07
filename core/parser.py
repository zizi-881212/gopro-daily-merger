import os
import datetime

class GoProParser:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def get_daily_groups(self):
        """
        掃描目標資料夾，回傳按日期分類且排序好的 GoPro 檔案字典。
        回傳格式: { '2024-04-01': ['GX010001.MP4', 'GX020001.MP4'], ... }
        """
        video_groups = {}
        
        if not os.path.isdir(self.folder_path):
            return video_groups

        for file in os.listdir(self.folder_path):
            # 篩選出 GoPro 格式的 MP4 檔案 (例如: GX010123.MP4)
            if file.upper().endswith('.MP4') and file.upper().startswith('GX'):
                full_path = os.path.join(self.folder_path, file)
                
                # 取得檔案修改時間並轉換為 YYYY-MM-DD 格式
                mtime = os.path.getmtime(full_path)
                date_key = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                
                if date_key not in video_groups:
                    video_groups[date_key] = []
                
                video_groups[date_key].append(file)

        # 針對每一天的檔案陣列進行 GoPro 命名規則排序
        for date_key in video_groups:
            video_groups[date_key] = self._sort_gopro_files(video_groups[date_key])
            
        return video_groups

    def _sort_gopro_files(self, file_list):
        """
        GoPro 命名邏輯：GX[章節:2碼][群組:4碼].MP4
        排序優先級：先按群組排，再按章節排
        """
        def sort_key(filename):
            # 確保檔名夠長才進行切片，避免 IndexError
            if len(filename) >= 12:
                chapter = filename[2:4]
                group = filename[4:8]
                return (group, chapter)
            return (filename, "")
            
        return sorted(file_list, key=sort_key)

# 簡單的本地測試區塊
if __name__ == "__main__":
    # 你可以把 test_dir 換成你電腦裡實際放 GoPro 影片的資料夾路徑來測試
    test_dir = "./" 
    parser = GoProParser(test_dir)
    groups = parser.get_daily_groups()
    
    for date, files in groups.items():
        print(f"日期: {date}")
        for f in files:
            print(f"  - {f}")