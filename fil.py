import csv
import os
import ast
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

class CSVImageReviewer:
    def __init__(self, root):
        self.root = root
        self.root.title("图像标注审核工具 - 正式版")
        self.root.geometry("1400x900")
        
        # 初始化数据
        self.data = []          
        self.current_index = 0  
        self.img_cache = {}     
        self.csv_path = ""      
        self.image_base = ""    
        self.zoom_level = 1.0
        
        # 创建界面
        self.create_widgets()
        self.setup_controls_state(False)

    def create_widgets(self):
        """创建主界面"""
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧70%区域
        left_frame = ttk.Frame(main_frame, width=int(1400 * 0.7))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.setup_left_pane(left_frame)

        # 右侧30%区域
        right_frame = ttk.Frame(main_frame, width=int(1400 * 0.3))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.setup_right_pane(right_frame)

        # 工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="加载CSV", command=self.load_csv).pack(side=tk.LEFT)
    
    def on_canvas_configure(self, event):
        """调整画布滚动区域"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def setup_left_pane(self, parent):
        """左侧主图区域"""
        # 添加滚动条容器
        self.canvas_frame = ttk.Frame(parent)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # 主画布
        self.main_canvas = tk.Canvas(self.canvas_frame, bg='#202020', cursor="crosshair")
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.main_canvas.yview)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.configure(yscrollcommand=self.v_scroll.set)

        # 水平滚动条
        self.h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.main_canvas.xview)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.main_canvas.configure(xscrollcommand=self.h_scroll.set)

        # 绑定鼠标滚轮事件
        self.main_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.main_canvas.bind("<Configure>", self.on_canvas_configure)


    def setup_right_pane(self, parent):
        """右侧控制面板"""
        # 放大视图
        zoom_frame = ttk.LabelFrame(parent, text="局部放大")
        zoom_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.zoom_canvas = tk.Canvas(zoom_frame, bg='#303030')
        self.zoom_canvas.pack(fill=tk.BOTH, expand=True)

        # 信息展示
        info_frame = ttk.LabelFrame(parent, text="标注信息")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="内容:", font=('微软雅黑', 14)).grid(row=0, column=0, sticky="w")
        self.instruction_label = ttk.Label(info_frame, text="", wraplength=380, font=('微软雅黑', 14))
        self.instruction_label.grid(row=0, column=1, sticky="w")
        
        ttk.Label(info_frame, text="类型:", font=('微软雅黑', 14)).grid(row=1, column=0, sticky="w")
        self.source_label = ttk.Label(info_frame, text="", font=('微软雅黑', 14))
        self.source_label.grid(row=1, column=1, sticky="w")

        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.status_var, font=('微软雅黑', 14)).pack(pady=5)

        # 操作按钮（修复部分）
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.prev_btn = ttk.Button(control_frame, text="◀ 上一张", command=self.prev_item)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.del_btn = ttk.Button(control_frame, text="✖ 删除标记", command=self.toggle_delete)
        self.del_btn.pack(side=tk.LEFT, padx=10)
        
        self.next_btn = ttk.Button(control_frame, text="下一张 ▶", command=self.next_item)
        self.next_btn.pack(side=tk.LEFT)
        
        # 保存按钮
        self.save_btn = ttk.Button(parent, text="💾 保存CSV", command=self.save_csv)
        self.save_btn.pack(pady=10)
    def load_csv(self):
        """加载CSV文件流程"""
        # 选择CSV文件
        csv_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not csv_path: return
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                temp_data = list(reader)
                
                # 第二步：选择图片根目录并验证
                image_base = self.select_and_validate_image_base(temp_data)
                if not image_base:
                    return  # 用户取消或验证失败
                
                # 初始化数据
                self.csv_path = csv_path
                self.image_base = image_base
                self.data = [dict(row, delete='False') for row in temp_data]
                self.current_index = 0
                
                self.setup_controls_state(True)
                self.show_current_item()
                messagebox.showinfo("加载成功", f"成功加载 {len(self.data)} 条记录")
                
        except Exception as e:
            messagebox.showerror("错误", f"文件加载失败:\n{str(e)}")

    def select_and_validate_image_base(self, data) -> str:
        """选择并验证图片根目录"""
        while True:
            # 选择根目录
            image_base = filedialog.askdirectory(
                title="选择图片根目录",
                mustexist=True
            )
            if not image_base:  # 用户取消选择
                return ""
            
            # 验证前20个文件是否存在
            sample_size = min(20, len(data))
            missing_files = []
            
            for i in range(sample_size):
                rel_path = data[i]['img_filename'].lstrip('/')
                full_path = os.path.join(image_base, rel_path)
                if not os.path.exists(full_path):
                    missing_files.append(rel_path)
                    
                # 更新进度
                self.status_var.set(f"正在验证文件 ({i+1}/{sample_size})...")
                self.root.update()
            
            if missing_files:
                msg = f"发现{len(missing_files)}个缺失文件，例如：\n{missing_files[:3]}\n请重新选择正确目录"
                messagebox.showerror("目录验证失败", msg)
            else:
                # 完整验证所有文件
                confirm = messagebox.askyesno(
                    "验证通过", 
                    f"抽样检查{sample_size}个文件全部存在\n是否要验证全部{len(data)}个文件？"
                )
                if confirm:
                    return self.full_validate(image_base, data)
                return image_base
            
    def full_validate(self, base_path, data) -> str:
        """完整验证所有文件"""
        missing_files = []
        total = len(data)
        
        for idx, row in enumerate(data):
            rel_path = row['img_filename'].lstrip('/')
            full_path = os.path.join(base_path, rel_path)
            if not os.path.exists(full_path):
                missing_files.append(rel_path)
            
            # 更新进度
            progress = idx + 1
            self.status_var.set(f"验证进度: {progress}/{total} ({len(missing_files)}缺失)")
            self.root.update()
        
        if missing_files:
            msg = f"共发现{len(missing_files)}个缺失文件，例如：\n{missing_files[:3]}\n请重新选择正确目录"
            messagebox.showerror("完整验证失败", msg)
            return ""
        return base_path

    def get_full_path(self, filename):
        """获取完整图片路径"""
        return os.path.normpath(os.path.join(
            self.image_base, 
            filename.lstrip('/')
        ))

    def show_current_item(self):
        """显示当前条目"""
        if not self.data: return
        
        row = self.data[self.current_index]
        img_path = self.get_full_path(row['img_filename'])
        
        try:
            # 加载图片
            if img_path not in self.img_cache:
                img = Image.open(img_path)
                self.img_cache[img_path] = {
                    'original': img,
                    'bbox': self.parse_bbox(row['bbox'])
                }
                # 计算初始缩放比例
                canvas_width = self.main_canvas.winfo_width() - 20
                canvas_height = self.main_canvas.winfo_height() - 20
                width_ratio = canvas_width / img.width
                height_ratio = canvas_height / img.height
                self.zoom_level = min(width_ratio, height_ratio)

            bbox = self.parse_bbox(row['bbox'])
            
            # 显示主图
            self.display_main_image(img_path, bbox)
            
            # 显示放大图
            self.display_zoom_view(img_path, bbox)
            
            # 更新信息
            self.update_info_panel(row)

        except Exception as e:
            messagebox.showerror("错误", f"图片加载失败:\n{str(e)}")
            self.next_item()

    def parse_bbox(self, bbox_str):
        """解析边界框"""
        try:
            return ast.literal_eval(bbox_str)
        except:
            return (0, 0, 100, 100)

    def display_main_image(self, img_path, bbox):
        """显示主图"""
        img_data = self.img_cache[img_path]
        img = img_data['original']

        
        
        # 缩放处理

        scaled_w = int(img.width * self.zoom_level)
        scaled_h = int(img.height * self.zoom_level)
        scaled_img = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        
        # 绘制边界框
        draw = ImageDraw.Draw(scaled_img)
        scaled_bbox = (
            bbox[0] * self.zoom_level,
            bbox[1] * self.zoom_level,
            bbox[2] * self.zoom_level,
            bbox[3] * self.zoom_level
        )
        draw.rectangle(scaled_bbox, outline='red', width=int(3*self.zoom_level))
        
        # 更新画布
        self.main_photo = ImageTk.PhotoImage(scaled_img)
        self.main_canvas.delete("all")
        self.main_canvas.create_image(0, 0, anchor=tk.NW, image=self.main_photo)
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def display_zoom_view(self, img_path, bbox):
        """显示局部放大"""
        img_data = self.img_cache[img_path]
        img = img_data['original']
        
        # 裁剪区域
        crop_img = img.crop(bbox)
        
        # 计算最佳缩放
        canvas_w = self.zoom_canvas.winfo_width() - 20
        canvas_h = self.zoom_canvas.winfo_height() - 20
        ratio = min(canvas_w/crop_img.width, canvas_h/crop_img.height)
        new_size = (int(crop_img.width*ratio), int(crop_img.height*ratio))
        
        # 高质量缩放
        zoom_img = crop_img.resize(new_size, Image.Resampling.LANCZOS)
        self.zoom_photo = ImageTk.PhotoImage(zoom_img)
        
        # 居中显示
        self.zoom_canvas.delete("all")
        x = (self.zoom_canvas.winfo_width() - new_size[0]) // 2
        y = (self.zoom_canvas.winfo_height() - new_size[1]) // 2
        self.zoom_canvas.create_image(x, y, anchor=tk.NW, image=self.zoom_photo)

    def update_info_panel(self, row):
        """更新信息面板"""
        self.instruction_label.config(text=row['instruction'])
        self.source_label.config(text=row['data_source'])
        status = f"记录: {self.current_index+1}/{len(self.data)} | 缩放: {self.zoom_level:.1f}x | 删除标记: {row['delete']}"
        self.status_var.set(status)

    def on_mousewheel(self, event):
        """鼠标滚轮缩放"""
        self.zoom_level *= 1.1 if event.delta > 0 else 0.9
        self.zoom_level = max(0.5, min(self.zoom_level, 5.0))
        self.show_current_item()

    def toggle_delete(self):
        """切换删除标记"""
        if self.data:
            current = self.data[self.current_index]['delete']
            new_state = 'False' if current == 'True' else 'True'
            self.data[self.current_index]['delete'] = new_state
            self.show_current_item()
    

    def next_item(self):
        """下一张"""
        if self.current_index < len(self.data)-1:
            self.current_index += 1
            self.show_current_item()

    def prev_item(self):
        """上一张"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_item()

    def save_csv(self):
        """保存CSV文件"""
        if not self.data: return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if save_path:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.data[0].keys())
                writer.writeheader()
                writer.writerows(self.data)
            messagebox.showinfo("保存成功", f"文件已保存至:\n{save_path}")

    def setup_controls_state(self, enabled):
        """设置控件状态"""
        state = "normal" if enabled else "disabled"
        for btn in [self.prev_btn, self.del_btn, self.next_btn]:
            btn.config(state=state)

if __name__ == "__main__":
    root = tk.Tk()
    app = CSVImageReviewer(root)
    root.mainloop()