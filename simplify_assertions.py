#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化断言示例 - 直接修改格式示例中的assertions
"""

FILE_PATH = "services/ai-processing/main_sqlite.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到assertions示例的位置(第464-469行)
# 需要将4个断言简化为2个

# 查找包含assertions的行
for i, line in enumerate(lines):
    if '"assertions": [' in line and i > 460 and i < 470:
        print(f"找到assertions示例在第 {i+1} 行")
        
        # 替换接下来的几行
        # 原来有4个断言,现在只保留2个
        new_assertions = [
            '              \"assertions\": [\n',
            '                {\"type\": \"status_code\", \"expected\": 200, \"description\": \"HTTP状态码应为200\"},\n',
            '                {\"type\": \"field_value\", \"field\": \"code\", \"expected\": 0, \"description\": \"业务状态码应为0\"}\n',
            '              ], \n'
        ]
        
        # 找到assertions结束的位置(下一个],)
        end_index = i
        for j in range(i+1, min(i+10, len(lines))):
            if '], ' in lines[j] or '],' in lines[j]:
                end_index = j
                break
        
        print(f"assertions结束在第 {end_index+1} 行")
        print(f"将替换第 {i+1} 到 {end_index+1} 行")
        
        # 替换这些行
        lines[i:end_index+1] = new_assertions
        
        # 写回文件
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("\n✅ 文件已更新!")
        print("\n新的assertions示例:")
        print("=" * 60)
        for line in new_assertions:
            print(line, end='')
        print("=" * 60)
        break
else:
    print("❌ 未找到assertions示例")
