import os
import subprocess
import json
import datetime
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import *
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from plyer import notification
import multiprocessing

VALID_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.ts', '.webm'}

class VideoConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("视频批量转换器")
        self.root.geometry("520x320")

        self.input_dir = StringVar()
        self.progress = IntVar()
        self.cancel_flag = threading.Event()
        self.thread_pool = None

        Label(root, text="选择视频文件夹:").pack(pady=10)
        Entry(root, textvariable=self.input_dir, width=50).pack(pady=5)
        Button(root, text="浏览", command=self.browse_directory).pack()

        self.start_btn = Button(root, text="开始转换", command=self.start_conversion_thread, state=DISABLED)
        self.start_btn.pack(pady=10)

        self.cancel_btn = Button(root, text="取消转换", command=self.cancel_conversion, state=DISABLED)
        self.cancel_btn.pack()

        self.progress_bar = Progressbar(root, orient=HORIZONTAL, length=400, mode='determinate', variable=self.progress)
        self.progress_bar.pack(pady=10)

        self.status_label = Label(root, text="等待开始")
        self.status_label.pack(pady=5)

        self.input_dir.trace_add("write", self.on_path_change)
        self.check_buttons_state()

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.input_dir.set(path)

    def on_path_change(self, *_):
        self.check_buttons_state()

    def check_buttons_state(self):
        path = self.input_dir.get()
        if os.path.isdir(path):
            self.start_btn.config(state=NORMAL)
        else:
            self.start_btn.config(state=DISABLED)
        self.cancel_btn.config(state=DISABLED)

    def cancel_conversion(self):
        self.cancel_flag.set()
        self.status_label.config(text="正在取消...")
        self.cancel_btn.config(state=DISABLED)

    def start_conversion_thread(self):
        self.start_btn.config(state=DISABLED)
        self.cancel_btn.config(state=NORMAL)
        self.cancel_flag.clear()
        t = threading.Thread(target=self.convert_all_videos)
        t.start()

    def convert_all_videos(self):
        input_dir = self.input_dir.get()
        output_dir = os.path.join(input_dir, 'Converted')
        log_dir = os.path.join(input_dir, 'Logs')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

        video_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir)
                       for f in files if self.is_video_file(os.path.join(root, f))]

        total = len(video_files)
        if total == 0:
            messagebox.showinfo("提示", "未找到支持的视频文件。")
            self.status_label.config(text="未找到支持的视频")
            self.check_buttons_state()
            return

        self.progress_bar['maximum'] = total
        self.progress.set(0)

        success, failed = 0, []
        cpu_count = max(multiprocessing.cpu_count() - 1, 1)
        self.thread_pool = ThreadPoolExecutor(max_workers=cpu_count)

        futures = {
            self.thread_pool.submit(self.process_video, idx, file, input_dir, output_dir, log_dir): file
            for idx, file in enumerate(video_files, 1)
        }

        for idx, future in enumerate(as_completed(futures), 1):
            if self.cancel_flag.is_set():
                break
            result = future.result()
            if result[0]:
                success += 1
            else:
                failed.append(result[1])
            self.root.after(0, self.progress.set, idx)
            self.root.after(0, self.status_label.config, {'text': f"处理进度 {idx}/{total}"})

        self.thread_pool.shutdown(wait=False)

        summary = f"转换完成：成功 {success}/{total}，失败 {len(failed)}"
        if failed:
            summary += f"\n失败：{', '.join([os.path.basename(f) for f in failed[:3]])} 等"

        notification.notify(title="视频转换器", message=summary, app_name="Video Converter", timeout=10)
        self.root.after(0, self.status_label.config, {'text': summary})
        self.root.after(0, self.check_buttons_state)

    def process_video(self, idx, input_file, input_dir, output_dir, log_dir):
        if self.cancel_flag.is_set():
            return False, input_file

        try:
            width, height, framerate = self.get_video_info(input_file)
            bitrate, crf = self.get_adaptive_params(width, height, framerate)

            rel = os.path.relpath(input_file, input_dir)
            out_file = os.path.join(output_dir, os.path.splitext(rel)[0] + '_hevc.mp4')
            log_file = os.path.join(log_dir, os.path.basename(input_file) + f"_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)

            if self.convert_video(input_file, out_file, log_file, bitrate, crf):
                return True, input_file
        except:
            pass
        return False, input_file

    def is_video_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in VALID_EXTENSIONS:
            return False
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-select_streams', 'v:0', path],
                                    capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return 'codec_type=video' in result.stdout
        except:
            return False

    def get_video_info(self, path):
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                     '-show_entries', 'stream=width,height,r_frame_rate',
                                     '-of', 'json', path],
                                    capture_output=True, text=True, encoding='utf-8', errors='ignore')
            info = json.loads(result.stdout)
            w = info['streams'][0]['width']
            h = info['streams'][0]['height']
            fr_str = info['streams'][0]['r_frame_rate']
            fr = eval(fr_str)
            return w, h, fr
        except:
            return 1920, 1080, 30

    def get_adaptive_params(self, w, h, fr):
        if w <= 720: bitrate = "800k"; crf = 24
        elif w <= 1280: bitrate = "1500k"; crf = 23
        elif w <= 1920: bitrate = "3000k"; crf = 22
        elif w <= 2560: bitrate = "4500k"; crf = 21
        else: bitrate = "6000k"; crf = 20
        if fr > 30:
            num = int(bitrate[:-1])
            bitrate = f"{int(num * 1.2)}k"
        return bitrate, crf

    def convert_video(self, infile, outfile, logfile, bitrate, crf):
        cmd = ['ffmpeg', '-hwaccel', 'vulkan', '-i', infile, '-c:v', 'hevc_amf', '-rc_mode', 'VBR_LATENCY',
               '-b:v', bitrate, '-c:a', 'copy', '-f', 'mp4', outfile, '-y']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0 and os.path.exists(outfile):
                return True
        except:
            pass

        # fallback
        cmd = ['ffmpeg', '-hwaccel', 'vulkan', '-i', infile, '-vf', 'scale_vulkan', '-c:v', 'libx265',
               '-crf', str(crf), '-preset', 'medium', '-c:a', 'copy', '-f', 'mp4', outfile, '-y']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return result.returncode == 0 and os.path.exists(outfile)
        except:
            return False

if __name__ == '__main__':
    root = Tk()
    app = VideoConverterGUI(root)
    root.mainloop()
