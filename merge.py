import os
import json
import csv
import zipfile
from typing import List

def validate_metadata(data: dict) -> bool:
    """验证元数据是否包含必要字段"""
    required_fields = {'cap_area', 'cap_full', 'crop_area_rel', 'crop_area_abs'}
    return all(field in data for field in required_fields)

def find_valid_image_ids(folder_path: str) -> List[str]:
    """查找所有包含有效元数据的image_id目录"""
    valid_ids = []
    for entry in os.scandir(folder_path):
        if entry.is_dir():
            meta_path = os.path.join(entry.path, 'image_meta.json')
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        data = json.load(f)
                        if validate_metadata(data):
                            valid_ids.append(entry.name)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"跳过无效元数据文件 {meta_path}: {str(e)}")
    return valid_ids

def create_merged_csv(app_name: str, image_ids: List[str]) -> str:
    """创建合并后的CSV文件"""
    csv_path = os.path.join(app_name, 'merged_data.csv')
    
    # 获取统一的app名称
    default_app = os.path.basename(os.path.normpath(app_name))
    app_value = input(f"请输入应用名称 (默认: {default_app}): ").strip() or default_app

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'image_id', 
            'cap_area', 
            'cap_full',
            'crop_area_rel',
            'crop_area_abs',
            'app',
            'image_path'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for img_id in image_ids:
            meta_path = os.path.join(app_name, img_id, 'image_meta.json')
            with open(meta_path, 'r') as f:
                data = json.load(f)
                writer.writerow({
                    'image_id': img_id,
                    'cap_area': json.dumps(data['cap_area']),
                    'cap_full': json.dumps(data['cap_full']),
                    'crop_area_rel': json.dumps(data['crop_area_rel']),
                    'crop_area_abs': json.dumps(data['crop_area_abs']),
                    'app': app_value,
                    'image_path': f"{img_id}/crop_image.jpg"
                })
    return csv_path

def create_zip_package(app_name: str, image_ids: List[str]):
    """创建压缩包并包含必要文件"""
    zip_filename = f"{app_name}_package.zip"
    base_path = os.path.abspath(app_name)
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加CSV文件
        csv_path = os.path.join(app_name, 'merged_data.csv')
        if os.path.exists(csv_path):
            zipf.write(csv_path, os.path.relpath(csv_path, base_path))
        
        # 添加图片目录
        for img_id in image_ids:
            img_dir = os.path.join(app_name, img_id)
            for root, _, files in os.walk(img_dir):
                for file in files:
                    if file.endswith(('.jpg', '.json')):
                        full_path = os.path.join(root, file)
                        zipf.write(
                            full_path, 
                            os.path.relpath(full_path, base_path)
                        )
    print(f"已创建压缩包: {os.path.abspath(zip_filename)}")

def main():
    app_folder = input("请输入APP目录路径: ").strip()
    
    if not os.path.isdir(app_folder):
        print(f"错误: 目录 {app_folder} 不存在")
        return

    valid_ids = find_valid_image_ids(app_folder)
    if not valid_ids:
        print("没有找到包含完整元数据的image_id目录")
        return

    print(f"找到 {len(valid_ids)} 个有效image_id目录")
    csv_file = create_merged_csv(app_folder, valid_ids)
    print(f"合并完成 -> {csv_file}")

    if input("是否创建压缩包? (y/n): ").lower() == 'y':
        create_zip_package(app_folder, valid_ids)

if __name__ == "__main__":
    main()