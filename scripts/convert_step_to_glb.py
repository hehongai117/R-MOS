#!/usr/bin/env python3
"""
convert_step_to_glb.py - 将 STEP 文件转换为 GLB 格式

使用 cadquery-ocp 读取 STEP 文件，导出为 STL，再用 trimesh 转换为 GLB
"""

import os
import sys
from pathlib import Path

# 模型目录
PARTS_DIR = Path("/Users/xuhehong/Desktop/r-mos/r-mos-frontend/public/models/parts")

def convert_step_to_glb(step_path: Path) -> bool:
    """使用 OCP 将 STEP 转换为 GLB"""
    try:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.StlAPI import StlAPI_Writer
        import trimesh
        
        # 读取 STEP 文件
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(step_path))
        
        if status != IFSelect_RetDone:
            print(f"  无法读取: {step_path.name}")
            return False
        
        reader.TransferRoots()
        shape = reader.OneShape()
        
        # 网格化
        mesh = BRepMesh_IncrementalMesh(shape, 0.1)
        mesh.Perform()
        
        # 导出为临时 STL
        stl_path = step_path.parent / (step_path.stem + '_temp.stl')
        writer = StlAPI_Writer()
        writer.Write(shape, str(stl_path))
        
        # 用 trimesh 转换为 GLB
        mesh = trimesh.load(str(stl_path))
        glb_path = step_path.with_suffix('.glb')
        mesh.export(str(glb_path))
        
        # 删除临时文件
        stl_path.unlink()
        
        print(f"  ✅ {step_path.name} -> {glb_path.name}")
        return True
        
    except Exception as e:
        print(f"  ❌ {step_path.name}: {e}")
        return False

def convert_stl_to_glb(stl_path: Path) -> bool:
    """使用 trimesh 将 STL 转换为 GLB"""
    try:
        import trimesh
        
        # 检查是否已有 GLB
        glb_path = stl_path.with_suffix('.glb')
        if glb_path.exists():
            return True  # 已转换
        
        mesh = trimesh.load(str(stl_path))
        mesh.export(str(glb_path))
        print(f"  ✅ {stl_path.name} -> {glb_path.name}")
        return True
        
    except Exception as e:
        print(f"  ❌ {stl_path.name}: {e}")
        return False

def main():
    print("=" * 60)
    print("R-MOS STEP/STL -> GLB 转换工具")
    print("=" * 60)
    
    # 统计
    step_files = []
    stl_files = []
    
    # 扫描所有子目录
    for category_dir in PARTS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for f in category_dir.iterdir():
            ext = f.suffix.lower()
            if ext in ['.step', '.stp']:
                # 检查是否已有对应 GLB
                glb_path = f.with_suffix('.glb')
                if not glb_path.exists():
                    step_files.append(f)
            elif ext == '.stl':
                glb_path = f.with_suffix('.glb')
                if not glb_path.exists():
                    stl_files.append(f)
    
    print(f"\n待转换文件:")
    print(f"  STEP: {len(step_files)}")
    print(f"  STL: {len(stl_files)}")
    
    # 转换 STL 文件
    if stl_files:
        print(f"\n转换 STL 文件...")
        stl_success = 0
        for f in stl_files:
            if convert_stl_to_glb(f):
                stl_success += 1
        print(f"STL 转换完成: {stl_success}/{len(stl_files)}")
    
    # 转换 STEP 文件
    if step_files:
        print(f"\n转换 STEP 文件...")
        step_success = 0
        for f in step_files:
            if convert_step_to_glb(f):
                step_success += 1
        print(f"STEP 转换完成: {step_success}/{len(step_files)}")
    
    # 更新 manifest
    print("\n更新模型清单...")
    import json
    manifest = {}
    for category_dir in PARTS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        files = [f.name for f in category_dir.iterdir() if not f.name.startswith('.')]
        manifest[category_dir.name] = sorted(files)
    
    manifest_path = PARTS_DIR / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # 统计 GLB 数量
    glb_count = sum(1 for cat in manifest.values() for f in cat if f.endswith('.glb'))
    print(f"\n总计 GLB 文件: {glb_count}")
    print("=" * 60)

if __name__ == '__main__':
    main()
