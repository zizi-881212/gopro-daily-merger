import os
import json
import shutil

class AppUtils:
    CONFIG_FILE = "config.json"

    @staticmethod
    def get_free_space_gb(path):
        """取得路徑所在硬碟的剩餘空間 (GB)"""
        # 取得磁碟根目錄 (例如 D:\)
        drive = os.path.splitdrive(os.path.abspath(path))[0]
        usage = shutil.disk_usage(drive or "/")
        return usage.free / (1024**3)

    @staticmethod
    def save_config(data):
        """將設定存入 json"""
        try:
            with open(AppUtils.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def load_config():
        """讀取 json 設定檔"""
        if os.path.exists(AppUtils.CONFIG_FILE):
            try:
                with open(AppUtils.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}