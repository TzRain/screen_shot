

# 0. 安装

## 安装方法

0. [可选],使用venv创建虚拟环境 `python -m venv [venv_name]` 后使用 `.\[venv_name]\Scripts\activate` 激活
   
1. 安装依赖文件 `pip install -r requirements.txt`


# 1. 截图

## 使用方法

### 选择app

1. 运行 `python run.py` 文件以启动工具。

2. 将出现一个窗口，列出正在运行的应用程序。

3. 从列表中选择所需的应用程序，然后点击“确认”按钮。

4. 将出现一个对话框，要求输入保存截图的文件夹名称。

5. 输入有效的文件夹名称[app_name]（不包含中文字符），然后点击“确认”。

   本次的所有全屏截图和应用截图都会保留在 `./[base_save_path]/[app_name]/[image_id]/ `

### 开始录制

1. 工具将根据选择的模式（自动或手动）开始捕获截图。
   
2. 按 `F9` 手动捕获截图。
   
3. 按 `F10` 停止录制。

## 配置

工具使用名为 `config.yaml` 的配置文件，该文件位于可执行文件所在的目录中。

您可以编辑此文件以更改以下设置：

- `base_save_path`: 保存截图的基本目录。
- `threshold`: 用于检测重复截图的相似度阈值。
- `capture_mode`: 捕获模式（`auto` 或 `manual`）。
- `auto_screenshot_interval`: 自动截图的时间间隔（秒）。
- `min_screenshot_interval`: 截图之间的最小时间间隔（秒）。
- `recent_screenshots_count`: 用于重复检测的最近截图数量。
- `jpeg_quality`: JPEG 压缩质量（0-100）。



# 2. 裁切

## 使用方法

### 选择目录

1. 运行 `python crop.py` 文件启动工具。
   
2. 选择需要的app_name为的文件目录,即为 `./[base_save_path]/[app_name]`

3. 依次浏览图片，并裁剪，如果不需要则“跳过”，每次只需要裁剪新增UI的区域即可（第一张或者变化很大的图片则全截图）。
   


# 3. merge

## 使用方法

1. 运行 `python merge.py `

2. 输入文件 app_name 的文件夹位置,即为 `./[base_save_path]/[app_name]`

3. 决定是否打包成一个压缩文件 


# 故障排除

- 自动截图时，确保文件夹名称不包含中文字符，否则截图文件可能不能正常保存
- 自动截图时，确保应用程序窗口未最小化或隐藏。
