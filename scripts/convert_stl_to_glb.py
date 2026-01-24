#!/usr/bin/env python3
"""
STL to GLB 批量转换脚本
用于将 Atom01 机器人的 STL 网格文件转换为 Web 友好的 GLB 格式

使用方法:
    python3 convert_stl_to_glb.py

输入: robot/roboto_origin/modules/atom01_description/meshes/*.STL
输出: r-mos-frontend/public/models/atom01/*.glb
"""

import os
import trimesh
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
STL_DIR = PROJECT_ROOT / "robot" / "roboto_origin" / "modules" / "atom01_description" / "meshes"
OUTPUT_DIR = PROJECT_ROOT / "r-mos-frontend" / "public" / "models" / "atom01"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def convert_stl_to_glb(stl_path: Path, output_path: Path) -> bool:
    """将单个 STL 文件转换为 GLB 格式"""
    try:
        # 加载 STL 网格
        mesh = trimesh.load(stl_path)
        
        # 如果是场景，提取网格
        if isinstance(mesh, trimesh.Scene):
            # 合并所有几何体
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if meshes:
                mesh = trimesh.util.concatenate(meshes)
            else:
                print(f"  ⚠️ 无法提取网格: {stl_path.name}")
                return False
        
        # 转换为场景（GLB 需要场景格式）
        scene = trimesh.Scene(geometry={'mesh': mesh})
        
        # 导出为 GLB
        scene.export(output_path, file_type='glb')
        
        # 获取文件大小
        size_kb = output_path.stat().st_size / 1024
        print(f"  ✅ {stl_path.name} → {output_path.name} ({size_kb:.1f} KB)")
        return True
        
    except Exception as e:
        print(f"  ❌ 转换失败 {stl_path.name}: {e}")
        return False

def main():
    print("=" * 60)
    print("Atom01 STL → GLB 批量转换")
    print("=" * 60)
    print(f"\n源目录: {STL_DIR}")
    print(f"输出目录: {OUTPUT_DIR}\n")
    
    # 查找所有 STL 文件
    stl_files = list(STL_DIR.glob("*.STL")) + list(STL_DIR.glob("*.stl"))
    
    if not stl_files:
        print("❌ 未找到 STL 文件")
        return
    
    print(f"找到 {len(stl_files)} 个 STL 文件\n")
    
    success_count = 0
    fail_count = 0
    
    for stl_path in sorted(stl_files):
        # 生成输出文件名 (小写, .glb 扩展名)
        output_name = stl_path.stem.lower() + ".glb"
        output_path = OUTPUT_DIR / output_name
        
        if convert_stl_to_glb(stl_path, output_path):
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"转换完成: {success_count} 成功, {fail_count} 失败")
    print("=" * 60)
    
    # 计算总大小
    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.glb"))
    print(f"总输出大小: {total_size / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
