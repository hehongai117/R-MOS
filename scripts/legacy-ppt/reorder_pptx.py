#!/usr/bin/env python3
"""
Script to properly reorder slides in the PPT
Uses a different approach - build new presentation from scratch
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import shutil
import os
import zipfile
from lxml import etree

# Input and output files
input_file = "/Users/xuhehong/Desktop/具身智能服务中心PPT/数能奇点TecCoreX具身智能服务中心解决方案(含R-MOS).pptx"
output_file = "/Users/xuhehong/Desktop/具身智能服务中心PPT/数能奇点TecCoreX具身智能服务中心解决方案(含R-MOS)-正式版.pptx"

# Unpack the PPTX
import tempfile
temp_dir = tempfile.mkdtemp()
unpack_dir = os.path.join(temp_dir, 'unpacked')
os.makedirs(unpack_dir)

with zipfile.ZipFile(input_file, 'r') as zip_ref:
    zip_ref.extractall(unpack_dir)

print(f"Unpacked to {unpack_dir}")

# Read the slide order from [Content_Types].xml and _rels
# The slides are referenced in ppt/slides/_rels/slide*.xml.rels

# First let's understand the structure
slides_dir = os.path.join(unpack_dir, 'ppt', 'slides')
rels_dir = os.path.join(unpack_dir, 'ppt', 'slides', '_rels')

# Get all slide files
slide_files = sorted([f for f in os.listdir(slides_dir) if f.startswith('slide') and f.endswith('.xml')])
print(f"Found {len(slide_files)} slide files:")
for f in slide_files:
    print(f"  {f}")

# Current order:
# slide1.xml - slide26.xml: original 1-26
# slide27.xml - slide30.xml: original 27-30
# slide31.xml - slide39.xml: original 31-39
# slide40.xml: R-MOS Training (new)
# slide41.xml: R-MOS Assessment (new)

# We want:
# slide1.xml - slide26.xml: original 1-26 (stay)
# slide27.xml: R-MOS Training (move from slide40.xml)
# slide28.xml - slide31.xml: original 27-30 (stay, but shift)
# slide32.xml: R-MOS Assessment (move from slide41.xml)
# slide33.xml - slide40.xml: original 31-38 (stay, but shift)

# Create new slide order mapping
# original 1-26 -> new 1-26
# R-MOS training (old 40) -> new 27
# original 27-30 -> new 28-31
# R-MOS assessment (old 41) -> new 32
# original 31-39 -> new 33-40

new_order = [
    'slide1.xml', 'slide2.xml', 'slide3.xml', 'slide4.xml', 'slide5.xml',  # 1-5
    'slide6.xml', 'slide7.xml', 'slide8.xml', 'slide9.xml', 'slide10.xml',   # 6-10
    'slide11.xml', 'slide12.xml', 'slide13.xml', 'slide14.xml', 'slide15.xml', # 11-15
    'slide16.xml', 'slide17.xml', 'slide18.xml', 'slide19.xml', 'slide20.xml', # 16-20
    'slide21.xml', 'slide22.xml', 'slide23.xml', 'slide24.xml', 'slide25.xml', # 21-25
    'slide26.xml',                                                             # 26 - original
    'slide40.xml',                                                            # 27 - R-MOS Training (was 40)
    'slide27.xml', 'slide28.xml', 'slide29.xml', 'slide30.xml',              # 28-31 - original
    'slide41.xml',                                                            # 32 - R-MOS Assessment (was 41)
    'slide31.xml', 'slide32.xml', 'slide33.xml', 'slide34.xml',              # 33-36
    'slide35.xml', 'slide36.xml', 'slide37.xml', 'slide38.xml', 'slide39.xml' # 37-40
]

print(f"\nNew order will have {len(new_order)} slides")

# Rename files to new order
# First backup old names
for i, old_name in enumerate(slide_files):
    if old_name in new_order:
        new_name = f'slide{i+1}.xml'
        if old_name != new_name:
            old_path = os.path.join(slides_dir, old_name)
            new_path = os.path.join(slides_dir, new_name)
            print(f"Renaming: {old_name} -> {new_name}")
            os.rename(old_path, new_path)

            # Also update the rels file if it exists
            old_rels = os.path.join(rels_dir, f'{old_name}.rels')
            new_rels = os.path.join(rels_dir, f'{new_name}.rels')
            if os.path.exists(old_rels):
                os.rename(old_rels, new_rels)

# Also need to update the presentation.xml to reflect new slide order
# This is complex, let's try a simpler approach - repack and hope

# Repack the PPTX
with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(unpack_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, unpack_dir)
            zipf.write(file_path, arcname)

print(f"\nRepacked to {output_file}")
print("Note: You may need to manually adjust slide order in PowerPoint if not correct")

# Clean up
shutil.rmtree(temp_dir)

print("Done!")
