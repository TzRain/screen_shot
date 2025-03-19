import cv2
import pyautogui
import time
import os
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import yaml
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from skimage.metrics import structural_similarity as ssim
import pygetwindow as gw
import keyboard
import mouse
import numpy as np
from collections import deque

CONFIG_FILE = "config.yaml"

# 加载和保存配置
def load_config():
    try:
        with open(CONFIG_FILE, "r") as file: # yaml
            config = yaml.safe_load(file)
            return config
            
    except FileNotFoundError:
        default_config = {
            "base_save_path": "screenshots",
            "azure_sas_url": "",
            "container_name": "",
            "threshold": 0.995,
            "upload_to_cloud": False,
            "capture_mode": "auto",
            "auto_screenshot_interval": 0.5, # x秒没有截屏就自动截屏
            "min_screenshot_interval": 0.1,  # 最短的截屏间隔是y秒
            "recent_screenshots_count": 5,   # 最近的k张截图
            "jpeg_quality": 100               # JPEG压缩质量（0-100）
        }
        with open(CONFIG_FILE, "w") as file:
            yaml.dump(default_config, file)
        return default_config

# 录制器类
class AppUsageRecorder:
    def __init__(self, app_window, save_folder_name, config):
        windows = gw.getWindowsWithTitle(app_window)
        if not windows:
            raise ValueError(f"未找到窗口: {app_window}")
        
        self.app_window = windows[0]  # 选择第一个匹配的窗口
        self.app_window.activate()  # 激活窗口，确保它可见

        self.base_save_path = os.path.join(config["base_save_path"], save_folder_name)
        # self.save_path_full = os.path.join(self.base_save_path, save_folder_name, "full_screen")
        # self.save_path_app = os.path.join(self.base_save_path, save_folder_name, "app_area")
        # self.save_meta_data = os.path.join(self.base_save_path, save_folder_name, "meta_data")
        self.azure_sas_url = config["azure_sas_url"]
        self.container_name = config["container_name"]
        self.threshold = config["threshold"]
        self.upload_to_cloud = config["upload_to_cloud"]
        self.capture_mode = config["capture_mode"]
        self.auto_screenshot_interval = config["auto_screenshot_interval"]
        self.min_screenshot_interval = config["min_screenshot_interval"]
        self.recent_screenshots_count = config["recent_screenshots_count"]
        self.jpeg_quality = config["jpeg_quality"]
        self.recent_frames = deque(maxlen=self.recent_screenshots_count)
        self.blob_service_client = BlobServiceClient(account_url=self.azure_sas_url) if self.azure_sas_url else None
        self.collection_count = 0

        if not os.path.exists(self.base_save_path):
            os.makedirs(self.base_save_path)

        # if not os.path.exists(self.save_path_full):
        #     os.makedirs(self.save_path_full)
        # if not os.path.exists(self.save_path_app):
        #     os.makedirs(self.save_path_app)

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
            return frame, (x, y, width, height)
        except Exception as e:
            print(f"窗口捕获失败: {e} 捕获全屏替代")
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame, (0, 0, frame.shape[1], frame.shape[0])

    def capture_full_screen(self):
        """ 截取全屏，返回彩色截图 """
        screenshot = pyautogui.screenshot()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame, (0, 0, frame.shape[1], frame.shape[0])

    def is_duplicate(self, current_frame):
        """ 判断当前截图是否与最近的 k 张截图重复 """
        gray_current_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        for recent_frame in list(self.recent_frames):  # 创建 deque 的副本进行迭代
            gray_recent_frame = cv2.cvtColor(recent_frame, cv2.COLOR_BGR2GRAY)
            try:
                similarity = ssim(gray_recent_frame, gray_current_frame)
            except Exception as e:
                similarity = 0

            if similarity > self.threshold:
                return True
        return False

    def save_frame(self, frame, path, name):
        filename = os.path.join(path, f"{name}.jpg")
        cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
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
        
        last_screenshot_time = time.time()

        def take_screenshot(reason):
            frame, frame_area = self.capture_window()
            full_frame, full_frame_area = self.capture_full_screen()
            
            if frame is not None and not self.is_duplicate(frame):
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                save_path = os.path.join(self.base_save_path, timestamp)
                os.makedirs(save_path, exist_ok=True)
                self.save_frame(frame, save_path,'cap_area_image')
                self.save_frame(full_frame, save_path,'cap_full_image')
                meta_data = {
                    "image_id": timestamp,
                    "cap_area": frame_area,
                    "cap_full": full_frame_area
                }
                with open(os.path.join(save_path, f"image_meta.json"), "w") as file:
                    json.dump(meta_data, file)

                self.recent_frames.append(frame)
                print(f"{reason} - 截图保存成功 {self.collection_count}")
                self.collection_count += 1
            else:
                print(f"{reason} - 截图重复，跳过")
        
        while not self.stop_recording:
            current_time = time.time()
            if current_time - last_screenshot_time >= self.auto_screenshot_interval:
                take_screenshot("时间间隔")
                last_screenshot_time = current_time
            elif keyboard.is_pressed("F9"):
                take_screenshot("手动截图")
                time.sleep(self.min_screenshot_interval)  
            elif mouse.is_pressed():
                take_screenshot("鼠标活动")
                time.sleep(self.min_screenshot_interval)
            
            time.sleep(0.05)
        
        print("录制结束")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("输入配置信息")
    config = load_config()

    mode_var = tk.StringVar(value=config["capture_mode"])
    mode_frame = tk.Frame(root)
    tk.Label(mode_frame, text="选择采样模式:").pack(side=tk.LEFT)
    tk.Radiobutton(mode_frame, text="自动", variable=mode_var, value="auto", command=lambda: config.update({"capture_mode": "auto"})).pack(side=tk.LEFT)
    tk.Radiobutton(mode_frame, text="手动", variable=mode_var, value="manual", command=lambda: config.update({"capture_mode": "manual"})).pack(side=tk.LEFT)
    mode_frame.pack()

    windows = gw.getAllTitles()
    windows = [w for w in windows if w.strip()]
    
    def select_window(window_name):
        save_folder_name = simpledialog.askstring("文件夹名称", "请输入保存截图的文件夹名称:(不允许包含中文!!!)", initialvalue=window_name)
        # 需要修改save_folder_name 去掉一些不合法的字符 和空格
        save_folder_name = ''.join([i for i in save_folder_name if not '\u4e00' <= i <= '\u9fff'])
        save_folder_name = save_folder_name.replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").removeprefix(" ").removesuffix(" ").replace(" ", "_")
        # 自动删去中文字符
        if not save_folder_name:
            messagebox.showerror("错误", "文件夹名称不能为空")
            return
        
        root.destroy()
        recorder = AppUsageRecorder(window_name, save_folder_name, config)
        messagebox.showinfo("信息", f"开始监听应用: {window_name}, 保存到: {save_folder_name}")
        recorder.start_recording(duration=60)
    
    for window in windows:
        tk.Button(root, text=window, command=lambda w=window: select_window(w)).pack(fill=tk.X)
    
    root.mainloop()
