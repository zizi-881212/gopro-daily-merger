import os
import datetime

class GoProParser:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def get_daily_groups(self):
        video_groups = {}
        if not os.path.isdir(self.folder_path):
            return video_groups

        valid_exts = ('.MP4', '.JPG', '.JPEG', '.PNG')

        for file in os.listdir(self.folder_path):
            if file.upper().endswith(valid_exts):
                full_path = os.path.join(self.folder_path, file)
                
                # 排除非 GoPro 的一般 MP4
                if file.upper().endswith('.MP4') and not file.upper().startswith('GX'):
                    continue

                mtime = os.path.getmtime(full_path)
                date_key = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                
                if date_key not in video_groups:
                    video_groups[date_key] = []
                
                video_groups[date_key].append(file)

        for date_key in video_groups:
            video_groups[date_key] = self._sort_gopro_files(video_groups[date_key])
            
        return video_groups

    def _sort_gopro_files(self, file_list):
        def sort_key(filename):
            if filename.upper().endswith('.MP4') and len(filename) >= 12:
                chapter = filename[2:4]
                group = filename[4:8]
                return (group, chapter)
            return (filename, "")
        return sorted(file_list, key=sort_key)