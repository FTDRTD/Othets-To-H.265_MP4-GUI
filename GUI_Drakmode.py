import os
import subprocess
import json
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from plyer import notification
import winreg  # Windows注册表，用于检测系统主题

CREATE_NO_WINDOW = 0x08000000  # 防止弹出控制台窗口
VALID_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.ts', '.webm'}

def is_windows_dark_mode():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize')
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # 0表示暗黑模式启用，1表示浅色模式
        return value == 0
    except Exception:
        return False

def monitor_system_theme(style, root, interval=5000):
    def check_and_switch():
        dark_mode = is_windows_dark_mode()
        current_theme = style.theme_use()
        target_theme = "darkly" if dark_mode else "flatly"
        if current_theme != target_theme:
            style.theme_use(target_theme)
        root.after(interval, check_and_switch)
    check_and_switch()

class VideoConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("视频批量转换器")
        self.root.geometry("550x320")

        self.style = tb.Style()  # 初始化样式
        monitor_system_theme(self.style, self.root)  # 启动系统夜间模式监听器

        self.input_dir = tb.StringVar()
        self.progress = tb.IntVar()
        self.total_files = 0
        self.cancelled = False
        self._stop_event = threading.Event()

        # 选择文件夹
        tb.Label(root, text="选择视频文件夹:", font=("微软雅黑", 12)).pack(pady=(15, 5))
        entry_frame = tb.Frame(root)
        entry_frame.pack(pady=5, fill=X, padx=15)
        self.entry = tb.Entry(entry_frame, textvariable=self.input_dir, bootstyle="info", width=45)
        self.entry.pack(side=LEFT, padx=(0, 10), fill=X, expand=True)
        tb.Button(entry_frame, text="浏览", command=self.browse_directory, bootstyle="info").pack(side=LEFT)

        # 开始和取消按钮
        btn_frame = tb.Frame(root)
        btn_frame.pack(pady=20)
        self.start_btn = tb.Button(btn_frame, text="开始转换", command=self.start_conversion_thread, bootstyle="success")
        self.start_btn.pack(side=LEFT, padx=10)
        self.cancel_btn = tb.Button(btn_frame, text="取消", command=self.cancel_conversion, bootstyle="danger", state=DISABLED)
        self.cancel_btn.pack(side=LEFT, padx=10)

        # 进度条
        self.progress_bar = tb.Progressbar(root, orient='horizontal', length=480, mode='determinate', variable=self.progress)
        self.progress_bar.pack(pady=10, padx=15)

        # 状态标签
        self.status_label = tb.Label(root, text="等待开始", font=("微软雅黑", 10))
        self.status_label.pack(pady=5)

        # 绑定输入框变化，控制按钮状态
        self.input_dir.trace_add('write', self.toggle_start_button)

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)

    def toggle_start_button(self, *args):
        if self.input_dir.get().strip():
            self.start_btn.config(state=NORMAL)
        else:
            self.start_btn.config(state=DISABLED)

    def start_conversion_thread(self):
        if not self.input_dir.get().strip():
            messagebox.showwarning("提示", "请选择视频文件夹！")
            return
        self.cancelled = False
        self._stop_event.clear()
        self.start_btn.config(state=DISABLED)
        self.cancel_btn.config(state=NORMAL)
        self.progress.set(0)
        self.status_label.config(text="正在扫描文件...")

        threading.Thread(target=self.convert_all_videos, daemon=True).start()

    def cancel_conversion(self):
        self.cancelled = True
        self._stop_event.set()
        self.status_label.config(text="取消中，请稍候...")

    def convert_all_videos(self):
        input_dir = self.input_dir.get().strip()
        if not os.path.exists(input_dir):
            self.show_error("路径不存在")
            self.reset_buttons()
            return

        video_files = []
        for root_dir, _, files in os.walk(input_dir):
            for f in files:
                full_path = os.path.join(root_dir, f)
                if self.is_video_file(full_path):
                    video_files.append(full_path)

        self.total_files = len(video_files)
        if self.total_files == 0:
            self.show_error("未找到有效视频文件")
            self.reset_buttons()
            return

        self.progress_bar['maximum'] = self.total_files
        self.status_label.config(text=f"准备转换 {self.total_files} 个文件")

        output_dir = os.path.join(input_dir, 'Converted')
        log_dir = os.path.join(input_dir, 'Logs')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

        success = 0
        failed = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for vf in video_files:
                if self._stop_event.is_set():
                    break
                futures.append(executor.submit(self.convert_single_video, vf, output_dir, log_dir))

            for idx, future in enumerate(as_completed(futures), 1):
                if self._stop_event.is_set():
                    break
                result, input_file = future.result()
                if result:
                    success += 1
                else:
                    failed.append(input_file)

                self.progress.set(idx)
                self.status_label.config(text=f"处理文件 {idx}/{self.total_files}")

        if self.cancelled:
            summary = f"转换已取消：完成 {success}/{self.total_files}"
        else:
            summary = f"转换完成：成功 {success}/{self.total_files}，失败 {len(failed)}"
            if failed:
                summary += f"\n失败示例：{', '.join([os.path.basename(f) for f in failed[:3]])} 等"

        notification.notify(title="视频转换器", message=summary, app_name="Video Converter", timeout=10)

        self.status_label.config(text=summary)
        self.reset_buttons()

    def convert_single_video(self, input_file, output_dir, log_dir):
        if self._stop_event.is_set():
            return False, input_file

        width, height, framerate = self.get_video_info(input_file)
        bitrate, crf = self.get_adaptive_params(width, height, framerate)

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        out_file = os.path.join(output_dir, base_name + '_hevc.mp4')
        log_file = os.path.join(log_dir, base_name + f"_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

        # 尝试硬件加速编码
        cmd = ['ffmpeg', '-hwaccel', 'vulkan', '-i', input_file, '-c:v', 'hevc_amf', '-rc_mode', 'VBR_LATENCY',
               '-b:v', bitrate, '-c:a', 'copy', '-f', 'mp4', out_file, '-y']

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
            if result.returncode == 0 and os.path.exists(out_file):
                return True, input_file
        except:
            pass

        # 软件编码fallback
        cmd = ['ffmpeg', '-hwaccel', 'vulkan', '-i', input_file, '-vf', 'scale_vulkan', '-c:v', 'libx265',
               '-crf', str(crf), '-preset', 'medium', '-c:a', 'copy', '-f', 'mp4', out_file, '-y']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
            return (result.returncode == 0 and os.path.exists(out_file)), input_file
        except:
            return False, input_file

    def is_video_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in VALID_EXTENSIONS:
            return False
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-select_streams', 'v:0', path],
                                    capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            return 'codec_type=video' in result.stdout
        except:
            return False

    def get_video_info(self, path):
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                     '-show_entries', 'stream=width,height,r_frame_rate',
                                     '-of', 'json', path], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            info = json.loads(result.stdout)
            w = info['streams'][0]['width']
            h = info['streams'][0]['height']
            fr_str = info['streams'][0]['r_frame_rate']
            fr = eval(fr_str)
            return w, h, fr
        except:
            return 1920, 1080, 30

    def get_adaptive_params(self, w, h, fr):
        if w <= 720:
            bitrate = "800k"
            crf = 24
        elif w <= 1280:
            bitrate = "1500k"
            crf = 23
        elif w <= 1920:
            bitrate = "3000k"
            crf = 22
        elif w <= 2560:
            bitrate = "4500k"
            crf = 21
        else:
            bitrate = "6000k"
            crf = 20
        if fr > 30:
            num = int(bitrate[:-1])
            bitrate = f"{int(num * 1.2)}k"
        return bitrate, crf

    def show_error(self, msg):
        self.root.after(0, lambda: messagebox.showerror("错误", msg))

    def reset_buttons(self):
        self.root.after(0, lambda: self.start_btn.config(state=NORMAL if self.input_dir.get().strip() else DISABLED))
        self.root.after(0, lambda: self.cancel_btn.config(state=DISABLED))


if __name__ == '__main__':
    root = tb.Window(title="视频批量转换器", themename="flatly")  # 初始浅色主题
    app = VideoConverterGUI(root)
    root.mainloop()
