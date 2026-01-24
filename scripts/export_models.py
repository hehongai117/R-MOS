#!/usr/bin/env python3
"""
export_models.py - 导出机器人模型文件到前端目录

功能：
1. 扫描 robot 目录下的所有模型文件
2. 按类别分类（螺丝、螺母、电机、标定件等）
3. 将 STEP/STL 文件转换为 GLB 格式供前端使用
"""

import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple

# 源目录和目标目录
ROBOT_DIR = Path("/Users/xuhehong/Desktop/r-mos/robot")
OUTPUT_DIR = Path("/Users/xuhehong/Desktop/r-mos/r-mos-frontend/public/models/parts")

# 文件分类规则
CATEGORY_RULES = {
    'screws': [
        r'螺钉', r'螺栓', r'screw', r'M\d+×\d+',
    ],
    'nuts': [
        r'螺母', r'nut', r'六角螺母',
    ],
    'motors': [
        r'电机', r'motor', r'DM\s*\d+', r'dm-j',
    ],
    'bearings': [
        r'轴承', r'bearing', r'AXK', r'十字轴承',
    ],
    'calibration': [
        r'标定', r'calibrat',
    ],
    'frames': [
        r'手臂', r'腿', r'脚', r'胸腔', r'髋', r'肩', r'大腿', r'小腿', r'腰',
        r'link', r'连杆', r'连接', r'夹板', r'支撑', r'底盖',
    ],
    'tools': [
        r'工具', r'tool', r'扳手',
    ],
}

def categorize_file(filename: str) -> str:
    """根据文件名判断类别"""
    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return category
    return 'misc'

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除特殊字符"""
    # 移除 GB 标准号前缀
    name = re.sub(r'GB[╱/]T\s*[\d\.\-]+\s*\[', '', filename)
    name = name.replace(']', '')
    # 替换特殊字符
    name = re.sub(r'[×]', 'x', name)
    name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff\.]', '', name)
    return name

def find_model_files(directory: Path) -> List[Tuple[Path, str]]:
    """查找所有模型文件"""
    extensions = {'.stl', '.step', '.stp', '.sldprt', '.sldasm'}
    files = []
    
    for root, dirs, filenames in os.walk(directory):
        # 跳过临时文件
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in filenames:
            if filename.startswith('~$'):
                continue
            ext = Path(filename).suffix.lower()
            if ext in extensions:
                filepath = Path(root) / filename
                category = categorize_file(filename)
                files.append((filepath, category))
    
    return files

def convert_to_glb(input_path: Path, output_path: Path) -> bool:
    """使用 trimesh 转换模型到 GLB 格式"""
    try:
        import trimesh
        mesh = trimesh.load(str(input_path))
        # 导出为 GLB
        glb_path = output_path.with_suffix('.glb')
        mesh.export(str(glb_path))
        return True
    except Exception as e:
        print(f"转换失败 {input_path.name}: {e}")
        return False

def main():
    print("=" * 60)
    print("R-MOS 模型导出工具")
    print("=" * 60)
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for category in list(CATEGORY_RULES.keys()) + ['misc']:
        (OUTPUT_DIR / category).mkdir(exist_ok=True)
    
    # 查找所有模型文件
    print("\n扫描模型文件...")
    files = find_model_files(ROBOT_DIR)
    print(f"找到 {len(files)} 个模型文件")
    
    # 统计各类别
    category_counts: Dict[str, int] = {}
    for _, cat in files:
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n各类别文件数量:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")
    
    # 复制 STEP/STL 文件到目标目录
    print("\n复制文件...")
    copied = 0
    converted = 0
    
    # 检查是否有 trimesh
    has_trimesh = False
    try:
        import trimesh
        has_trimesh = True
        print("检测到 trimesh，将尝试转换 STEP/STL -> GLB")
    except ImportError:
        print("未安装 trimesh，仅复制源文件")
    
    for filepath, category in files:
        # 目标路径
        new_name = sanitize_filename(filepath.name)
        dest_dir = OUTPUT_DIR / category
        dest_path = dest_dir / new_name
        
        # 避免覆盖
        if dest_path.exists():
            base = dest_path.stem
            ext = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_dir / f"{base}_{counter}{ext}"
                counter += 1
        
        # 复制文件
        try:
            shutil.copy2(filepath, dest_path)
            copied += 1
            
            # 尝试转换为 GLB
            if has_trimesh and filepath.suffix.lower() in {'.stl', '.step', '.stp'}:
                if convert_to_glb(dest_path, dest_path):
                    converted += 1
                    
        except Exception as e:
            print(f"复制失败 {filepath.name}: {e}")
    
    print(f"\n完成! 复制 {copied} 个文件, 转换 {converted} 个 GLB")
    
    # 生成清单
    print("\n生成模型清单...")
    manifest_path = OUTPUT_DIR / "manifest.json"
    import json
    
    manifest = {}
    for category in os.listdir(OUTPUT_DIR):
        cat_path = OUTPUT_DIR / category
        if cat_path.is_dir():
            files_list = [f for f in os.listdir(cat_path) if not f.startswith('.')]
            manifest[category] = sorted(files_list)
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"清单已保存到: {manifest_path}")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
