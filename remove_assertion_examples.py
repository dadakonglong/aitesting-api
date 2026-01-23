#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除断言示例中的 field_exists 和 response_contains
"""

FILE_PATH = "services/ai-processing/main_sqlite.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到并删除包含 field_exists 和 response_contains 的示例行
lines_to_delete = []
for i, line in enumerate(lines):
    if i > 435 and i < 445:
        if "field_exists" in line or "response_contains" in line:
            lines_to_delete.append(i)
            print(f"标记删除第{i+1}行: {line.strip()}")

# 从后往前删除
for i in reversed(lines_to_delete):
    del lines[i]

# 写回文件
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n✅ 已删除 {len(lines_to_delete)} 行断言示例")
print("\n现在只保留两个断言示例:")
print("  1. status_code")
print("  2. field_value (业务码)")
