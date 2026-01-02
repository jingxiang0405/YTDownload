import customtkinter as ctk
import yt_dlp
import threading
import tkinter as tk
import os
import sys
import subprocess
from pathlib import Path
import platform # *** 1. 引入 platform 函式庫 ***

# --- 主應用程式設定 ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 視窗設定 ---
        self.title("YouTube 下載器")
        self.geometry("700x480")
        self.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.info_dict = None
        self.video_title_str = tk.StringVar()
        
        self.DOWNLOAD_DIR = os.path.join(Path.home(), "Downloads")
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)

        # --- UI 元件 ---
        self.title_label = ctk.CTkLabel(self, text="YouTube 媒體下載器", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.pack(pady=10, padx=20, fill="x")
        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="請在此貼上 YouTube 影片網址", width=400)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.fetch_button = ctk.CTkButton(self.url_frame, text="獲取資訊", width=100, command=self.start_fetch_thread)
        self.fetch_button.pack(side="left", padx=5)

        self.video_title_label = ctk.CTkLabel(self, textvariable=self.video_title_str, font=ctk.CTkFont(size=14))
        self.video_title_label.pack(pady=5, padx=20)
        self.video_title_str.set("影片標題將顯示於此")

        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, padx=20, fill="x")
        
        self.download_type_label = ctk.CTkLabel(self.options_frame, text="下載類型:")
        self.download_type_label.pack(side="left", padx=10)
        self.download_type_var = ctk.StringVar(value="影片 (MP4)")
        self.download_type_menu = ctk.CTkSegmentedButton(self.options_frame, values=["影片 (MP4)", "音訊 (MP3)"],
                                                         variable=self.download_type_var, command=self.update_options_ui)
        self.download_type_menu.pack(side="left", padx=10)

        self.resolution_label = ctk.CTkLabel(self.options_frame, text="解析度:")
        self.resolution_var = ctk.StringVar(value="")
        self.resolution_menu = ctk.CTkOptionMenu(self.options_frame, variable=self.resolution_var, state="disabled")
        
        self.open_folder_var = ctk.BooleanVar(value=True)
        self.open_folder_checkbox = ctk.CTkCheckBox(self, text="下載完成後自動開啟資料夾", variable=self.open_folder_var)
        self.open_folder_checkbox.pack(pady=10)

        self.download_button = ctk.CTkButton(self, text="下載", command=self.start_download_thread, state="disabled")
        self.download_button.pack(pady=10)

        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="歡迎使用！檔案將儲存至系統的「下載」資料夾。")
        self.status_label.pack(pady=10)

        self.update_options_ui()

    def update_options_ui(self, value=None):
        if self.download_type_var.get() == "影片 (MP4)":
            self.resolution_label.pack(side="left", padx=(20, 5))
            self.resolution_menu.pack(side="left")
        else:
            self.resolution_label.pack_forget()
            self.resolution_menu.pack_forget()
        self.update_download_button_state()

    def start_fetch_thread(self):
        self.fetch_button.configure(state="disabled", text="獲取中...")
        self.status_label.configure(text="正在獲取影片資訊...")
        thread = threading.Thread(target=self.fetch_video_info, daemon=True)
        thread.start()

    def fetch_video_info(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.configure(text="錯誤：請先輸入網址！")
            self.fetch_button.configure(state="normal", text="獲取資訊")
            return

        try:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.info_dict = ydl.extract_info(url, download=False)
            
            self.video_title_str.set(self.info_dict.get('title', '無法獲取標題'))
            self.status_label.configure(text="資訊獲取成功！請選擇格式並下載。")
            
            formats = self.info_dict.get('formats', [])
            video_resolutions = sorted(
                list(set(
                    f"{f.get('height')}p" for f in formats 
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4' and f.get('height')
                )),
                key=lambda res: int(res.replace('p', ''))
            )

            if video_resolutions:
                self.resolution_menu.configure(values=video_resolutions)
                self.resolution_var.set(video_resolutions[-1])
                self.resolution_menu.configure(state="normal")
            else:
                self.resolution_menu.configure(values=["無可用格式"], state="disabled")
            
            self.update_download_button_state()

        except Exception:
            self.status_label.configure(text=f"錯誤：無法獲取影片資訊。")
            self.video_title_str.set("影片標題將顯示於此")
        finally:
            self.fetch_button.configure(state="normal", text="獲取資訊")

    def update_download_button_state(self):
        if self.info_dict:
            self.download_button.configure(state="normal")
        else:
            self.download_button.configure(state="disabled")

    def start_download_thread(self):
        self.download_button.configure(state="disabled")
        self.fetch_button.configure(state="disabled")
        self.open_folder_checkbox.configure(state="disabled")
        self.progress_bar.set(0)
        thread = threading.Thread(target=self.download_media, daemon=True)
        thread.start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                progress = d['downloaded_bytes'] / total_bytes
                self.after(0, lambda: self.progress_bar.set(progress))
                self.after(0, lambda: self.status_label.configure(text=f"下載中... {d['_percent_str']} ({d['_speed_str']})"))
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.configure(text="下載完成，正在進行後處理..."))

    # *** 2. 這是修改後的 open_folder 函式 ***
    def open_folder(self, path):
        """跨平台地開啟資料夾，並特別處理 WSL 的情況。"""
        try:
            if sys.platform == "win32":
                os.startfile(os.path.realpath(path))
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", path])
            else: # Linux and WSL
                # 透過 platform.uname() 檢查是否為 WSL
                if "microsoft" in platform.uname().release.lower() or "wsl" in platform.uname().release.lower():
                    # 在 WSL 中，呼叫 Windows 的 explorer.exe
                    subprocess.run(["explorer.exe", os.path.realpath(path)])
                else:
                    # 在原生的 Linux 桌面環境中，使用 xdg-open
                    subprocess.run(["xdg-open", path])
        except Exception as e:
            self.status_label.configure(text=f"無法開啟資料夾: {e}")

    def on_download_complete(self, success, error_msg=None):
        if success:
            if self.open_folder_var.get():
                self.status_label.configure(text="任務完成！正在開啟「下載」資料夾...")
                self.open_folder(self.DOWNLOAD_DIR)
            else:
                self.status_label.configure(text="任務完成！檔案已儲存至系統「下載」資料夾。")
        else:
            self.status_label.configure(text=f"下載失敗: {str(error_msg)[:100]}...")

        self.download_button.configure(state="normal")
        self.fetch_button.configure(state="normal")
        self.open_folder_checkbox.configure(state="normal")

    def download_media(self):
        url = self.url_entry.get()
        download_type = self.download_type_var.get()
        
        try:
            ydl_opts = {
                'progress_hooks': [self.progress_hook],
                'outtmpl': os.path.join(self.DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            }
            
            if download_type == "影片 (MP4)":
                chosen_resolution = self.resolution_var.get().replace('p', '')
                ydl_opts['format'] = f'bestvideo[height<={chosen_resolution}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            
            elif download_type == "音訊 (MP3)":
                ydl_opts['format'] = 'bestaudio/best'
                
                # *** 這是新增的修改 ***
                # 判斷程式是否被打包成 exe
                if getattr(sys, 'frozen', False):
                    # 如果是 exe，FFmpeg 會在暫存資料夾的根目錄
                    ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
                else:
                    # 如果是直接執行 .py，FFmpeg 在專案根目錄
                    ffmpeg_path = "."
                
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                # 明確告訴 yt-dlp FFmpeg 的位置
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.after(0, self.on_download_complete, True)

        except Exception as e:
            self.after(0, self.on_download_complete, False, e)

# --- 啟動應用程式 ---
if __name__ == "__main__":
    app = App()
    app.mainloop()
