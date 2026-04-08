import os
import datetime

class GoProParser:
    @staticmethod
    def get_sort_key(filepath):
        """統一的排序邏輯：GoPro影片/照片優先，其餘依時間排序"""
        fname = os.path.basename(filepath).upper()
        if fname.startswith('GX') and len(fname) >= 12:
            return (0, fname[4:8], fname[2:4]) # (優先權, 流水號, 章節)
        elif fname.startswith('GOPR') and len(fname) >= 12:
            return (0, fname[4:8], '00')       # 照片章節設為 '00'，排在同號影片前
        return (1, os.path.getmtime(filepath), fname) # 其他設備檔案依修改時間

    @staticmethod
    def group_files_by_date(file_paths):
        """將傳入的檔案清單依日期分組，並自動套用智慧排序"""
        groups = {}
        for file_path in file_paths:
            fname = os.path.basename(file_path).upper()
            # 判斷是否為 GoPro 影片或各式照片
            if fname.startswith('GX') or fname.endswith(('.JPG', '.PNG', '.JPEG')):
                mtime = os.path.getmtime(file_path)
                date_key = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                groups.setdefault(date_key, []).append(file_path)
            else:
                groups.setdefault('未分類', []).append(file_path)
        
        # 對每個分組進行內部排序，確保統一性
        for date_key in groups:
            groups[date_key].sort(key=GoProParser.get_sort_key)
            
        return groups