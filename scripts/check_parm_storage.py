#!/usr/bin/env python3
"""
检查 apis 表中 /vod/song/order 等接口的 request_body 存储格式，
重点确认 parm 字段是字符串还是对象。
"""
import json
import os
import sqlite3

# 定位数据库
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "apis.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(BASE, "services", "data", "apis.db")


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, path, method, summary, request_body FROM apis WHERE path LIKE '%song/order%' OR path LIKE '%vod%' ORDER BY id DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()
    print(f"找到 {len(rows)} 条相关接口\n")
    for r in rows:
        print(f"--- id={r['id']} {r['method']} {r['path']} ({r['summary'] or '(无)'}) ---")
        rb_raw = r["request_body"]
        if not rb_raw:
            print("  request_body: 空")
            continue
        try:
            rb = json.loads(rb_raw)
        except Exception:
            print(f"  request_body: 解析失败 (原始长度 {len(rb_raw)})")
            continue
        if isinstance(rb, dict):
            if "content" in rb and "properties" not in rb:
                print("  格式: OpenAPI 原始结构 (content/schema)，执行时无法直接使用")
                content = rb.get("content", {})
                for ct, med in (content or {}).items():
                    schema = (med or {}).get("schema", {})
                    props = (schema or {}).get("properties", {})
                    if props:
                        parm_def = props.get("parm", {})
                        if parm_def:
                            ex = parm_def.get("example", "(无)")
                            print(f"  parm 定义: example={repr(ex)[:80]}...")
                            print(f"  parm 类型: example 是字符串 -> 展平后应为字符串")
            else:
                parm = rb.get("parm")
                if "parm" in rb:
                    t = type(parm).__name__
                    print(f"  parm 存储: type={t}, value={repr(parm)[:100]}")
                    if isinstance(parm, dict):
                        print("  ⚠ parm 为对象！form 编码会错误序列化，需改为字符串")
                    else:
                        print("  ✓ parm 为字符串，格式正确")
                else:
                    print(f"  扁平字段: {list(rb.keys())[:15]}")
        else:
            print(f"  request_body 类型: {type(rb).__name__}")
        print()


if __name__ == "__main__":
    main()
