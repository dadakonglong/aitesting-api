#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终简化: 只保留 status_code 和 field_value 两种断言类型
移除 response_contains 和 json_path
"""

FILE_PATH = "services/ai-processing/main_sqlite.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修改类型列表(第430行左右)
for i, line in enumerate(lines):
    if "类型 (type) 必须是以下之一" in line and i > 425 and i < 435:
        old_line = line
        # 只保留 status_code 和 field_value
        new_line = line.replace(
            "'status_code', 'field_value', 'response_contains', 'json_path'",
            "'status_code', 'field_value'"
        )
        if new_line != old_line:
            lines[i] = new_line
            print(f"✅ 修改第{i+1}行: 只保留 status_code 和 field_value")
            print(f"   原: {old_line.strip()}")
            print(f"   新: {new_line.strip()}")

# 删除 response_contains 和 json_path 的规则说明
lines_to_delete = []
for i, line in enumerate(lines):
    if i > 425 and i < 440:
        if "'response_contains'" in line or "'json_path'" in line:
            lines_to_delete.append(i)
            print(f"✅ 标记删除第{i+1}行: {line.strip()}")

# 从后往前删除,避免索引变化
for i in reversed(lines_to_delete):
    del lines[i]

# 写回文件
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ 文件已更新!")
print("\n修改总结:")
print("=" * 60)
print("只保留两种最基本的断言类型:")
print("  1. status_code - HTTP状态码")
print("  2. field_value - 字段值验证")
print("=" * 60)
