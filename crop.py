import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# image_meta.json
# cap_full_image.jpg
# cap_area_image.jpg

class ImageCropperApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("交互式图像裁剪工具 v2.1")
        self.root.geometry("1000x700")
        
        # 初始化状态
        self.app_dir = None
        self.image_dirs = []
        self.current_index = -1  # 初始为-1表示未选择
        self.rect_start = None
        self.rect_end = None
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 顶部工具栏
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(fill=tk.X)
        
        tk.Button(toolbar, text="选择APP目录", command=self.select_app_dir).pack(side=tk.LEFT, padx=5, pady=3)
        self.dir_label = tk.Label(toolbar, text="未选择目录")
        self.dir_label.pack(side=tk.LEFT, padx=10)
        
        # 主显示区域
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图像显示区域
        self.canvas = tk.Canvas(main_frame, bg='#EEE', cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 控制面板
        control_frame = tk.Frame(main_frame)
        control_frame.pack(pady=10)
        
        self.btn_prev = tk.Button(control_frame, text="上一张", command=self.previous_image, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        
        self.btn_confirm = tk.Button(control_frame, text="确认裁剪", command=self.confirm_crop, state=tk.DISABLED)
        self.btn_confirm.pack(side=tk.LEFT, padx=5)
        
        self.btn_next = tk.Button(control_frame, text="跳过", command=self.next_image, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        self.progress_label = tk.Label(main_frame, text="就绪")
        self.progress_label.pack()
        
        # 绑定画布事件
        self.canvas.bind("<Button-1>", self.start_rect)
        self.canvas.bind("<B1-Motion>", self.draw_rect)
        self.canvas.bind("<ButtonRelease-1>", self.end_rect)

    def select_app_dir(self):
        """选择APP目录并初始化处理队列"""
        selected_dir = filedialog.askdirectory(title="选择包含image_id的APP目录")
        if selected_dir:
            self.app_dir = selected_dir
            self.dir_label.config(text=selected_dir)
            self.load_image_dirs()
            self.current_index = 0  # 初始化索引
            self.show_current_image()
            self.update_controls()

    def load_image_dirs(self):
        """加载所有有效的image_id目录"""
        self.image_dirs = []
        for dir_name in sorted(os.listdir(self.app_dir)):
            dir_path = os.path.join(self.app_dir, dir_name)
            if os.path.isdir(dir_path):
                required_files = {'cap_full_image.jpg', 'image_meta.json'}
                if required_files.issubset(os.listdir(dir_path)):
                    self.image_dirs.append(dir_path)

    def show_current_image(self):
        """显示当前目录的图像"""
        if 0 <= self.current_index < len(self.image_dirs):
            current_dir = self.image_dirs[self.current_index]
            img_path = os.path.join(current_dir, 'cap_full_image.jpg')
           
            try:
                img = Image.open(img_path)
                self.display_image(img)
                self.update_controls()
                self.update_progress()
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图像: {str(e)}")
                self.next_image()
        else:
            messagebox.showinfo("提示", "没有更多目录可处理")

    def display_image(self, image):
        """调整并显示图像"""
        # 计算显示尺寸
        canvas_width = self.canvas.winfo_width() - 20
        canvas_height = self.canvas.winfo_height() - 20
        img_width, img_height = image.size
       
        scale = min(canvas_width/img_width,
                   canvas_height/img_height)
        new_size = (int(img_width*scale), int(img_height*scale))
        
        # 保存缩放比例用于坐标转换
        self.scale_x = img_width / new_size[0]
        self.scale_y = img_height / new_size[1]
        
        # 显示图像
        self.tk_image = ImageTk.PhotoImage(image.resize(new_size))
        self.canvas.delete("all")
        self.canvas.create_image(10, 10, anchor=tk.NW, image=self.tk_image)
        self.rect_start = None
        self.rect_end = None

    def start_rect(self, event):
        """开始绘制矩形"""
        self.rect_start = (event.x, event.y)
        self.rect_end = None

    def draw_rect(self, event):
        """实时绘制矩形"""
        if self.rect_start:
            self.canvas.delete("rect")
            x0, y0 = self.rect_start
            x1, y1 = event.x, event.y
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                       outline='#00FF00', width=2, tags="rect")

    def end_rect(self, event):
        """结束矩形绘制"""
        self.rect_end = (event.x, event.y)
        self.canvas.delete("rect")
        self.canvas.create_rectangle(self.rect_start[0], self.rect_start[1],
                                   self.rect_end[0], self.rect_end[1],
                                   outline='#FF0000', width=2, tags="rect")

    def confirm_crop(self):
        """确认当前选择并保存结果"""
        if not self.rect_start or not self.rect_end:
            messagebox.showwarning("警告", "请先选择区域！")
            return
            
        # 计算实际坐标
        x0 = int(min(self.rect_start[0], self.rect_end[0]) * self.scale_x)
        y0 = int(min(self.rect_start[1], self.rect_end[1]) * self.scale_y)
        x1 = int(max(self.rect_start[0], self.rect_end[0]) * self.scale_x)
        y1 = int(max(self.rect_start[1], self.rect_end[1]) * self.scale_y)

        # 保存裁剪图像
        current_dir = self.image_dirs[self.current_index]
        img_path = os.path.join(current_dir, 'cap_full_image.jpg')
    
        try:
            img = Image.open(img_path)
            crop_img = img.crop((x0, y0, x1, y1))
            crop_img.save(os.path.join(current_dir, 'crop_image.jpg'), quality=95)
            
            # 更新元数据
            self.update_metadata(current_dir, x0, y0, x1, y1)
            self.next_image()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def previous_image(self):
        """返回上一张图像"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_image()
        else:
            messagebox.showinfo("提示", "已经是第一张图片")

    def next_image(self):
        """跳转到下一张图像"""
        if self.current_index < len(self.image_dirs) - 1:
            self.current_index += 1
            self.show_current_image()
        else:
            messagebox.showinfo("完成", "所有目录处理完成！")
            self.reset_controls()

    def update_controls(self):
        """更新控件状态"""
        has_images = len(self.image_dirs) > 0
        self.btn_prev.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        self.btn_confirm.config(state=tk.NORMAL if has_images else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if has_images else tk.DISABLED)

    def update_progress(self):
        """更新进度显示"""
        text = f"正在处理：{self.current_index + 1}/{len(self.image_dirs)}"
        self.progress_label.config(text=text)
    
    def update_metadata(self, dir_path, x0, y0, x1, y1):
        """更新JSON元数据文件"""
        meta_path = os.path.join(dir_path, 'image_meta.json')
        with open(meta_path, 'r+') as f:
            meta = json.load(f)
            cap_x, cap_y, _, _ = meta['cap_full']
           
            meta['crop_area_rel'] = [x0, y0, x1-x0, y1-y0]
            meta['crop_area_abs'] = [
                cap_x + x0,
                cap_y + y0,
                x1-x0,
                y1-y0
            ]
            f.seek(0)
            json.dump(meta, f, indent=4)
            f.truncate()
            
    def previous_image(self):
        """返回上一张图像"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_image()
        else:
            messagebox.showinfo("提示", "已经是第一张图片")



    def reset_controls(self):
        """重置控件状态"""
        self.btn_confirm.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)
        self.canvas.delete("all")
        self.progress_label.config(text="就绪")

    def update_progress(self):
        """更新进度显示"""
        text = f"正在处理：{self.current_index + 1}/{len(self.image_dirs)}"
        self.progress_label.config(text=text)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ImageCropperApp()
    app.run()