import cv2
import numpy as np
import pyautogui
import time
import os
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, ttk
import json
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from skimage.metrics import structural_similarity as ssim
import shutil
import pygetwindow as gw
import keyboard

CONFIG_FILE = "config.json"

# 加载和保存配置
def load_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "base_save_path": "screenshots",
            "azure_sas_url": "",
            "container_name": "",
            "threshold": 0.95,
            "min_frame_interval": 1,
            "video_fps": 30,
            "video_resolution": "1920x1080",
            "upload_to_cloud": False,
            "capture_mode": "manual"
        }

def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

# 编辑配置面板
def edit_config():
    config_window = tk.Toplevel(root)
    config_window.title("配置项面板")
    config_window.geometry("450x450")

    frame = tk.Frame(config_window)
    frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    entries = {}
    for key, value in config.items():
        row = tk.Frame(frame)
        label = tk.Label(row, text=key, width=20, anchor='w')
        if key == "base_save_path":
            entry = tk.Entry(row, width=30)
            entry.insert(0, str(value))
            browse_button = tk.Button(row, text="选择路径", command=lambda e=entry: e.delete(0, tk.END) or e.insert(0, filedialog.askdirectory(title="选择本地保存路径")))
            entries[key] = entry
            row.pack(fill=tk.X, pady=2)
            label.pack(side=tk.LEFT)
            entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
            browse_button.pack(side=tk.RIGHT)
        else:
            entry = tk.Entry(row)
            entry.insert(0, str(value))
            entries[key] = entry
            row.pack(fill=tk.X, pady=2)
            label.pack(side=tk.LEFT)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

    def confirm_changes():
        for key, entry in entries.items():
            new_value = entry.get()
            if key in ["threshold", "min_frame_interval", "video_fps"]:
                config[key] = float(new_value) if '.' in new_value else int(new_value)
            elif key == "upload_to_cloud":
                config[key] = new_value.lower() in ["true", "1", "yes"]
            else:
                config[key] = new_value
        save_config(config)
        messagebox.showinfo("信息", "配置已更新并保存！")
        config_window.destroy()

    def load_config_from_file():
        file_path = filedialog.askopenfilename(title="选择配置文件", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "r") as file:
                new_config = json.load(file)
                config.update(new_config)
                config_window.destroy()
                edit_config()
    
    def save_config_to_file():
        confirm_changes()
        file_path = filedialog.asksaveasfilename(title="保存配置文件", filetypes=[("JSON files", "*.json")], defaultextension="config.json")
        if file_path:
            with open(file_path, "w") as file:
                json.dump(config, file, indent=4)
            messagebox.showinfo("信息", "配置已保存到文件！")

    btn_frame = tk.Frame(config_window)
    btn_frame.pack(fill=tk.X, pady=10)
    tk.Button(btn_frame, text="加载配置", command=load_config_from_file).pack(side=tk.LEFT, expand=True)
    tk.Button(btn_frame, text="确认&导出配置", command=save_config_to_file).pack(side=tk.LEFT, expand=True)
    tk.Button(config_window, text="确认", command=confirm_changes).pack(pady=5)

# 录制器类
class AppUsageRecorder:
    def __init__(self, app_window, save_folder_name, config):
        windows = gw.getWindowsWithTitle(app_window)
        if not windows:
            raise ValueError(f"未找到窗口: {app_window}")
        
        self.app_window = windows[0]  # 选择第一个匹配的窗口
        self.app_window.activate()  # 激活窗口，确保它可见

        self.base_save_path = config["base_save_path"]
        self.save_path = os.path.join(self.base_save_path, save_folder_name)
        self.azure_sas_url = config["azure_sas_url"]
        self.container_name = config["container_name"]
        self.threshold = config["threshold"]
        self.min_frame_interval = config["min_frame_interval"]
        self.upload_to_cloud = config["upload_to_cloud"]
        self.capture_mode = config["capture_mode"]
        self.last_frame = None
        self.blob_service_client = BlobServiceClient(account_url=self.azure_sas_url) if self.azure_sas_url else None

        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def capture_window(self):
        """ 只截取目标窗口，返回彩色截图 """
        try:
            if self.app_window.isMinimized:  # 如果窗口最小化，则恢复
                self.app_window.restore()
            if not self.app_window.isActive:  # 如果窗口未激活，尝试激活
                try:
                    self.app_window.activate()
                except Exception as e:
                    print(f"窗口激活失败: {e}, 继续截图")
            
            x, y, width, height = (
                self.app_window.left, 
                self.app_window.top, 
                self.app_window.width, 
                self.app_window.height
            )
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            frame = np.array(screenshot)  # 保持彩色图像
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # 转换为 OpenCV BGR 格式
            return frame
        except Exception as e:
            print(f"窗口捕获失败: {e}")
            return None


        
    def has_ui_changed(self, current_frame):
        """ 计算 UI 变化 """
        if self.last_frame is None:
            self.last_frame = current_frame
            return True
        gray_last_frame = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
        gray_current_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        similarity = ssim(gray_last_frame, gray_current_frame)
        if similarity < self.threshold:
            self.last_frame = current_frame
            return True
        return False

    
    def save_frame(self, frame):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.save_path, f"{timestamp}.png")
        cv2.imwrite(filename, frame)
        return filename

    def start_recording(self, duration=30):
        """ 自动录制：只有 UI 变化时才截图 """
        print("开始录制... 按 F10 停止录制")
        start_time = time.time()
        self.stop_recording = False

        def stop_callback():
            self.stop_recording = True
            print("录制停止信号收到")
        
        keyboard.add_hotkey("F10", stop_callback)
        
        if self.capture_mode == "auto":
            while time.time() - start_time < duration and not self.stop_recording:
                frame = self.capture_window()
                if frame is not None and self.has_ui_changed(frame):
                    self.save_frame(frame)
                    print("Frame saved.")
                time.sleep(self.min_frame_interval)
        else:
            """ 手动模式：按 F9 截图 """
            print("按 F9 进行手动截图... 按 F10 停止录制")
            while time.time() - start_time < duration and not self.stop_recording:
                if keyboard.is_pressed("F9"):
                    frame = self.capture_window()
                    if frame is not None:
                        self.save_frame(frame)
                        print("手动截图已保存.")
                    time.sleep(0.5)
        
        self.upload_to_azure()
        print("录制结束")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("输入配置信息")
    config = load_config()

    tk.Button(root, text="编辑配置项", command=edit_config).pack(side=tk.TOP, anchor=tk.NE)

    mode_var = tk.StringVar(value=config["capture_mode"])
    mode_frame = tk.Frame(root)
    tk.Label(mode_frame, text="选择采样模式:").pack(side=tk.LEFT)
    tk.Radiobutton(mode_frame, text="自动", variable=mode_var, value="auto", command=lambda: config.update({"capture_mode": "auto"})).pack(side=tk.LEFT)
    tk.Radiobutton(mode_frame, text="手动", variable=mode_var, value="manual", command=lambda: config.update({"capture_mode": "manual"})).pack(side=tk.LEFT)
    mode_frame.pack()

    windows = gw.getAllTitles()
    windows = [w for w in windows if w.strip()]
    
    def select_window(window_name):
        save_folder_name = simpledialog.askstring("文件夹名称", "请输入保存截图的文件夹名称:", initialvalue=window_name)
        # 需要修改save_folder_name 去掉一些不合法的字符 和空格
        save_folder_name = save_folder_name.replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").removeprefix(" ").removesuffix(" ").replace(" ", "_")
        
        root.destroy()
        recorder = AppUsageRecorder(window_name, save_folder_name, config)
        messagebox.showinfo("信息", f"开始监听应用: {window_name}, 保存到: {save_folder_name}")
        recorder.start_recording(duration=60)
    
    for window in windows:
        tk.Button(root, text=window, command=lambda w=window: select_window(w)).pack(fill=tk.X)
    
    root.mainloop()
