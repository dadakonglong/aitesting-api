#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从断言类型列表中移除 field_exists
"""

FILE_PATH = "services/ai-processing/main_sqlite.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修改第430行 - 移除field_exists
if len(lines) > 429:
    old_line_430 = lines[429]
    if "'field_exists'" in old_line_430:
        # 移除 'field_exists',
        new_line_430 = old_line_430.replace("'field_exists', ", "")
        lines[429] = new_line_430
        print(f"✅ 修改第430行: 移除 'field_exists'")
        print(f"   原: {old_line_430.strip()}")
        print(f"   新: {new_line_430.strip()}")

# 修改第433行 - 移除field_exists的规则说明
if len(lines) > 432:
    # 删除第433行(field_exists的规则)
    if "'field_exists'" in lines[432]:
        print(f"✅ 删除第433行: {lines[432].strip()}")
        del lines[432]

# 写回文件
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ 文件已更新!")
print("\n修改总结:")
print("=" * 60)
print("1. 从类型列表中移除 'field_exists'")
print("2. 删除 field_exists 的规则说明")
print("=" * 60)
