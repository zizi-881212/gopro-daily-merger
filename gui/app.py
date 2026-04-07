import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from collections import defaultdict

from core.parser import GoProParser
from core.ffmpeg_runner import FFmpegRunner
from core.downloader import FFmpegDownloader

class GoProMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GoPro Daily Merger - FishOnJuice")
        self.root.geometry("650x650") 
        
        self.current_dir = os.getcwd()
        self.ffmpeg_path = os.path.join(self.current_dir, "ffmpeg.exe")
        
        self.target_folder = ""
        self.output_folder = ""
        
        self.setup_ui()

    def setup_ui(self):
        # 標題與品牌
        tk.Label(self.root, text="GoPro 影片自動排序與合併", font=("微軟正黑體", 16, "bold")).pack(pady=(15, 5))
        tk.Label(self.root, text="Developed by FishOnJuice", font=("Arial", 11, "italic"), fg="gray").pack(pady=(0, 10))

        # 1. 來源資料夾
        tk.Label(self.root, text="1. 選擇來源 (GoPro 原始檔)", font=("微軟正黑體", 10, "bold")).pack()
        self.folder_label = tk.Label(self.root, text="尚未選擇來源資料夾", fg="#0052cc", font=("微軟正黑體", 9))
        self.folder_label.pack(pady=2)
        tk.Button(self.root, text="選擇並預覽檔案", command=self.select_input_folder, width=25, bg="#e1f5fe").pack(pady=(0, 10))

        # 2. 輸出位置
        tk.Label(self.root, text="2. 選擇輸出位置 (選填)", font=("微軟正黑體", 10, "bold")).pack()
        self.output_label = tk.Label(self.root, text="預設：與來源資料夾相同", fg="gray", font=("微軟正黑體", 9))
        self.output_label.pack(pady=2)
        tk.Button(self.root, text="自訂輸出資料夾", command=self.select_output_folder, width=25).pack(pady=(0, 15))

        # 3. 執行按鈕
        self.run_btn = tk.Button(self.root, text="確認順序並開始合併", command=self.start_processing, state=tk.DISABLED, width=30, bg="#4CAF50", fg="black", font=("微軟正黑體", 11, "bold"))
        self.run_btn.pack(pady=10)

        # 狀態與預覽日誌區
        tk.Label(self.root, text="掃描預覽與執行日誌：", font=("微軟正黑體", 9)).pack(anchor="w", padx=25)
        self.log_area = scrolledtext.ScrolledText(self.root, width=80, height=18, state=tk.DISABLED, font=("Consolas", 9))
        self.log_area.pack(pady=5, padx=20)

    def log(self, message, clear=False):
        self.log_area.config(state=tk.NORMAL)
        if clear:
            self.log_area.delete('1.0', tk.END)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def select_input_folder(self):
        folder_path = filedialog.askdirectory(title="選擇 GoPro 影片來源資料夾")
        if folder_path:
            self.target_folder = folder_path
            self.folder_label.config(text=f"來源: {self.target_folder}")
            self.preview_scan() # 選擇後立刻執行預覽掃描

    def preview_scan(self):
        """掃描資料夾並列出結構化的預覽清單"""
        self.log("🔍 正在深度掃描資料夾內容...", clear=True)
        parser = GoProParser(self.target_folder)
        groups = parser.get_daily_groups()
        
        if not groups:
            self.log("⚠️ 找不到符合 GoPro 命名規則 (GX01xxxx.MP4) 的檔案。")
            self.run_btn.config(state=tk.DISABLED)
            return

        self.log(f"✅ 掃描完成！共發現 {len(groups)} 天的素材：\n")
        
        for date_key, files in groups.items():
            self.log(f"📅 日期：{date_key} (共 {len(files)} 個檔案)")
            
            # 進一步按 GoPro 群組 ID (後四碼) 分類顯示給使用者看
            sub_groups = defaultdict(list)
            for f in files:
                group_id = f[4:8]
                sub_groups[group_id].append(f)
            
            for gid, f_list in sub_groups.items():
                self.log(f"   📂 群組 {gid}: {' ➔ '.join(f_list)}")
            self.log("-" * 50)
            
        self.log("\n請檢查上方順序是否正確。若無誤，請點擊「開始合併」。")
        self.run_btn.config(state=tk.NORMAL)

    def select_output_folder(self):
        folder_path = filedialog.askdirectory(title="選擇成品要輸出的資料夾")
        if folder_path:
            self.output_folder = folder_path
            self.output_label.config(text=f"輸出: {self.output_folder}", fg="#0052cc")
            self.log(f"🎯 設定輸出路徑: {self.output_folder}")

    def start_processing(self):
        self.run_btn.config(state=tk.DISABLED)
        if not os.path.exists(self.ffmpeg_path):
            ans = messagebox.askyesno("缺少核心組件", "是否由 FishOnJuice 自動下載 FFmpeg？")
            if ans:
                threading.Thread(target=self.download_and_then_process, daemon=True).start()
            else:
                self.run_btn.config(state=tk.NORMAL)
            return
        
        threading.Thread(target=self.process_videos, daemon=True).start()

    def download_and_then_process(self):
        downloader = FFmpegDownloader()
        def log_callback(msg): self.root.after(0, self.log, msg)
        if downloader.download_and_extract(self.current_dir, log_callback):
            self.process_videos()
        else:
            self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))

    def process_videos(self):
        self.root.after(0, self.log, "\n" + "="*20 + " 開始執行合併 " + "="*20)
        parser = GoProParser(self.target_folder)
        groups = parser.get_daily_groups()
        runner = FFmpegRunner(self.ffmpeg_path)
        
        for date_key, files in groups.items():
            self.root.after(0, self.log, f"⏳ 處理中: {date_key}...")
            success = runner.merge_videos(date_key, files, self.target_folder, self.output_folder)
            self.root.after(0, self.log, f"✅ {date_key} 完成！" if success else f"❌ {date_key} 失敗。")

        self.root.after(0, self.log, "\n🎉 所有任務處理完畢！")
        self.root.after(0, lambda: messagebox.showinfo("完成", "合併任務已結束"))
        self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))