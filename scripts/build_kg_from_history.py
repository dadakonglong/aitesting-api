#!/usr/bin/env python3
"""
从历史 test_cases 构建知识图谱
将已有场景用例的 steps 和 param_mappings 转为图谱节点和边。
执行：python scripts/build_kg_from_history.py [--project PROJECT_ID]
"""
import os
import sys
import json
import sqlite3
import argparse

# 保证能导入项目模块
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

DB_PATH = os.path.join(BASE, "data", "apis.db")
KG_PATH = os.path.join(BASE, "data", "knowledge_graph.pkl")


def main():
    parser = argparse.ArgumentParser(description="从历史 test_cases 构建知识图谱")
    parser.add_argument("--project", default=None, help="仅处理指定 project_id，不指定则处理全部")
    args = parser.parse_args()

    if not os.path.isfile(DB_PATH):
        print(f"❌ 数据库不存在: {DB_PATH}")
        sys.exit(1)

    sys.path.insert(0, os.path.join(BASE, "services", "ai-processing"))
    try:
        from lightweight_services import LightweightKnowledgeGraph
    except ImportError as e:
        print(f"❌ 无法导入 LightweightKnowledgeGraph: {e}")
        sys.exit(1)

    kg = LightweightKnowledgeGraph(KG_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if args.project:
        cur.execute("SELECT id, name, steps, project_id FROM test_cases WHERE project_id = ?", (args.project,))
    else:
        cur.execute("SELECT id, name, steps, project_id FROM test_cases WHERE steps IS NOT NULL AND steps != ''")
    rows = cur.fetchall()
    conn.close()

    nodes_added = set()
    edges_added = 0

    for row in rows:
        tc_id = row["id"]
        project_id = row["project_id"] or "default-project"
        try:
            steps = json.loads(row["steps"] or "[]")
        except Exception:
            continue
        if not isinstance(steps, list) or not steps:
            continue

        steps_sorted = sorted(steps, key=lambda s: int(s.get("step_order") or 0))

        for s in steps_sorted:
            m = str(s.get("api_method") or s.get("method") or "GET").upper()
            p = str(s.get("api_path") or s.get("path") or "")
            if not p:
                continue
            nid = f"{project_id}:{m}:{p}"
            if nid not in nodes_added:
                kg.ensure_api_node(nid, path=p, method=m, name=s.get("description") or s.get("api_name") or "")
                nodes_added.add(nid)

        node_ids = []
        for s in steps_sorted:
            m = str(s.get("api_method") or s.get("method") or "GET").upper()
            p = str(s.get("api_path") or s.get("path") or "")
            node_ids.append(f"{project_id}:{m}:{p}")

        for i, s in enumerate(steps_sorted):
            mappings = s.get("param_mappings") or []
            if not mappings or i >= len(node_ids):
                continue
            to_nid = node_ids[i]
            by_from = {}
            for m in mappings:
                if not isinstance(m, dict):
                    continue
                fs = m.get("from_step")
                ff = m.get("from_field")
                tf = m.get("to_field")
                tt = m.get("to_type", "params")
                if fs is None or tf is None:
                    continue
                idx = int(fs) - 1
                if 0 <= idx < len(node_ids):
                    from_nid = node_ids[idx]
                    if from_nid not in by_from:
                        by_from[from_nid] = {}
                    by_from[from_nid][f"{tf}@{tt}"] = ff
            for from_nid, fm in by_from.items():
                field_mapping = dict(fm)
                kg.add_dependency(
                    from_nid, to_nid,
                    field_mapping=field_mapping,
                    source_type="manual",
                    source_id=f"tc:{tc_id}",
                    success=True,
                )
                edges_added += 1

    stats = kg.get_stats()
    print(f"✅ 完成。节点: {stats['total_apis']}, 边: {stats['total_dependencies']} (本次新增节点: {len(nodes_added)}, 边: {edges_added})")


if __name__ == "__main__":
    main()
