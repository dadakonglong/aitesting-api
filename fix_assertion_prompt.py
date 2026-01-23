#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改 main_sqlite.py 中的断言生成规则
添加准确性要求,减少断言数量
"""

FILE_PATH = "services/ai-processing/main_sqlite.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到目标行(第446行,索引445)
target_line_index = 445

if target_line_index < len(lines):
    old_line = lines[target_line_index]
    print(f"原始行 {target_line_index + 1}:")
    print(repr(old_line))
    
    # 检查是否是我们要修改的行
    if "每个步骤至少包含3个断言" in old_line:
        # 替换这一行,并在前面插入新的准确性要求
        new_lines = [
            '            - **断言准确性要求 (重要!)**：\n',
            '              * 断言必须符合API的实际功能,不要臆测不存在的字段\n',
            '              * 例如: 点歌接口验证"点歌成功"而非"订单ID",搜索接口验证"歌曲列表"而非"订单列表"\n',
            '              * 优先验证通用字段(code/message),避免验证不确定的业务字段\n',
            '              * 如果不确定响应结构,只验证HTTP状态码和业务状态码\n',
            '            - **每个步骤建议2-3个断言**: HTTP状态码(必需) + 业务状态码(推荐) + 消息验证(可选)\n'
        ]
        
        # 替换目标行
        lines[target_line_index:target_line_index+1] = new_lines
        
        # 写回文件
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("\n✅ 文件已更新!")
        print("\n新增内容:")
        print("=" * 60)
        for line in new_lines:
            print(line, end='')
        print("=" * 60)
    else:
        print("❌ 第446行内容不匹配,可能已经修改过了")
else:
    print(f"❌ 文件行数不足 {target_line_index + 1} 行")
