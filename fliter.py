import csv
import os
import ast
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

class CSVImageReviewer:
    def __init__(self, root):
        self.root = root
        self.root.title("图像标注审核工具")
        self.root.geometry("1200x800")

        # 初始化数据
        self.data = []          
        self.current_index = 0  
        self.img_cache = {}     
        self.csv_path = ""      
        self.image_base = ""    # 新增：图片根目录
        
        # 创建界面
        self.create_widgets()
        self.setup_controls_state(False)

    def create_widgets(self):
        """创建界面布局"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # 左上角按钮
        ttk.Button(toolbar, text="加载CSV", command=self.load_csv).pack(side=tk.LEFT)

        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧图片展示区
        left_frame = ttk.Frame(main_frame, width=600)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.main_canvas = tk.Canvas(left_frame, bg='#EEE')
        self.main_canvas.pack(fill=tk.BOTH, expand=True)

        # 右侧信息区
        right_frame = ttk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 信息展示
        info_frame = ttk.LabelFrame(right_frame, text="标注信息")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.instruction_label = ttk.Label(info_frame, text="Instruction: ")
        self.instruction_label.pack(anchor=tk.W)
        self.source_label = ttk.Label(info_frame, text="Data Source: ")
        self.source_label.pack(anchor=tk.W)

        # 放大视图
        self.zoom_frame = ttk.LabelFrame(right_frame, text="局部放大")
        self.zoom_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.zoom_canvas = tk.Canvas(self.zoom_frame)
        self.zoom_canvas.pack(fill=tk.BOTH, expand=True)

        # 操作按钮
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.prev_btn = ttk.Button(btn_frame, text="上一张", command=self.prev_item)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.del_btn = ttk.Button(btn_frame, text="标记删除", command=self.toggle_delete)
        self.del_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(btn_frame, text="下一张", command=self.next_item)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(right_frame, textvariable=self.status_var).pack(pady=5)
        
        # 保存按钮
        self.save_btn = ttk.Button(right_frame, text="保存CSV", command=self.save_csv)
        self.save_btn.pack(pady=10)

    def setup_controls_state(self, enabled=True):
        """设置控件状态"""
        state = "normal" if enabled else "disabled"
        for widget in [self.prev_btn, self.del_btn, self.next_btn, self.save_btn]:
            widget.config(state=state)

    def load_csv(self):
        """加载CSV文件（新增根目录验证）"""
        # 第一步：选择CSV文件
        csv_path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv")],
            title="选择标注文件"
        )
        if not csv_path:
            return
            
        try:
            # 读取CSV数据
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                temp_data = list(reader)
                
                # 第二步：选择图片根目录并验证
                image_base = self.select_and_validate_image_base(temp_data)
                if not image_base:
                    return  # 用户取消或验证失败
                
                # 验证通过后保存数据
                self.csv_path = csv_path
                self.image_base = image_base
                self.data = temp_data
                
                # 添加删除标记字段
                for row in self.data:
                    row['delete'] = 'False'
                
                self.current_index = 0
                self.setup_controls_state(True)
                self.show_current_item()
                messagebox.showinfo("加载成功", f"已加载 {len(self.data)} 条记录")
                
        except Exception as e:
            messagebox.showerror("加载失败", f"文件读取错误:\n{str(e)}")
            self.setup_controls_state(False)

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

    def get_full_image_path(self, filename):
        """获取完整图片路径（使用验证过的根目录）"""
        rel_path = filename.lstrip('/')
        return os.path.normpath(os.path.join(self.image_base, rel_path))

    def show_current_item(self):
        """显示当前条目（完整实现）"""
        if not self.data or self.current_index >= len(self.data):
            return

        row = self.data[self.current_index]
        img_path = self.get_full_image_path(row['img_filename'])
        
        try:
            # 缓存检查与加载
            if img_path not in self.img_cache:
                img = Image.open(img_path)
                self.img_cache[img_path] = {
                    'original': img,
                    'display': None,
                    'bbox': self.parse_bbox(row['bbox'])
                }
            
            img_data = self.img_cache[img_path]
            orig_img = img_data['original']
            
            # 生成显示图片（带缩放）
            display_img = orig_img.copy()
            display_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
            
            # 绘制边界框
            draw = ImageDraw.Draw(display_img)
            scaled_bbox = self.scale_bbox(
                img_data['bbox'], 
                orig_img.size, 
                display_img.size
            )
            draw.rectangle(scaled_bbox, outline='red', width=3)
            
            # 更新主画布
            self.main_photo = ImageTk.PhotoImage(display_img)
            self.main_canvas.delete("all")
            self.main_canvas.create_image(0, 0, anchor=tk.NW, image=self.main_photo)
            
            # 更新放大视图
            self.show_zoom_view(orig_img, img_data['bbox'])
            
            # 更新文字信息
            self.instruction_label.config(text=f"Instruction: {row['instruction']}")
            self.source_label.config(text=f"Data Source: {row['data_source']}")
            self.status_var.set(
                f"当前: {self.current_index+1}/{len(self.data)} | " 
                f"删除标记: {row['delete']} | "
                f"分辨率: {row['resolution']}"
            )
            
        except Exception as e:
            messagebox.showerror("图片加载错误", f"无法加载图片:\n{str(e)}")
            self.next_item()

    def parse_bbox(self, bbox_str):
        """解析边界框字符串"""
        try:
            return ast.literal_eval(bbox_str)  # 安全解析列表
        except:
            return (0, 0, 100, 100)  # 默认值

    def scale_bbox(self, bbox, orig_size, new_size):
        """坐标缩放转换"""
        orig_w, orig_h = orig_size
        new_w, new_h = new_size
        x_scale = new_w / orig_w
        y_scale = new_h / orig_h
        return (
            int(bbox[0] * x_scale),
            int(bbox[1] * y_scale),
            int(bbox[2] * x_scale),
            int(bbox[3] * y_scale)
        )

    def show_zoom_view(self, img, bbox):
        """显示局部放大图"""
        try:
            zoom_img = img.crop(bbox)
            zoom_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            self.zoom_photo = ImageTk.PhotoImage(zoom_img)
            self.zoom_canvas.delete("all")
            self.zoom_canvas.create_image(0, 0, anchor=tk.NW, image=self.zoom_photo)
        except Exception as e:
            print(f"局部视图错误: {str(e)}")

    def toggle_delete(self):
        """切换删除标记"""
        if self.data:
            current_state = self.data[self.current_index]['delete']
            new_state = 'False' if current_state == 'True' else 'True'
            self.data[self.current_index]['delete'] = new_state
            self.show_current_item()

    def next_item(self):
        """下一张"""
        if self.current_index < len(self.data) - 1:
            self.current_index += 1
            self.show_current_item()

    def prev_item(self):
        """上一张"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_item()

    def save_csv(self):
        """保存CSV文件"""
        if not self.data:
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if save_path:
            # 获取所有字段（保留原始顺序）
            fieldnames = list(self.data[0].keys())
            if 'delete' not in fieldnames:
                fieldnames.append('delete')
                
            # 写入文件
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)
            messagebox.showinfo("保存成功", f"文件已保存至: {save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CSVImageReviewer(root)
    root.mainloop()