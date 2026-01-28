"""
报告服务 - 数据聚合和分析

提供测试报告所需的各类统计数据和可视化数据
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict


class ReportService:
    def __init__(self, db_path: str = "test_platform.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    async def get_overview_stats(self, project_id: str, time_range: str = "7d") -> Dict:
        """
        获取概览统计数据
        
        Args:
            project_id: 项目ID
            time_range: 时间范围 (7d, 30d, 90d)
        
        Returns:
            {
                "total_executions": 100,
                "success_rate": 0.85,
                "avg_response_time": 234.5,
                "total_scenarios": 20,
                "active_scenarios": 15
            }
        """
        days = int(time_range.replace('d', ''))
        start_date = datetime.now() - timedelta(days=days)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 总执行次数
            cursor.execute("""
                SELECT COUNT(*) FROM test_executions 
                WHERE project_id = ? AND created_at >= ?
            """, (project_id, start_date))
            total_executions = cursor.fetchone()[0]
            
            # 成功次数
            cursor.execute("""
                SELECT COUNT(*) FROM test_executions 
                WHERE project_id = ? AND created_at >= ? AND status = 'success'
            """, (project_id, start_date))
            success_count = cursor.fetchone()[0]
            
            # 平均响应时间
            cursor.execute("""
                SELECT AVG(CAST(json_extract(result, '$.avg_response_time') AS REAL))
                FROM test_executions 
                WHERE project_id = ? AND created_at >= ? AND result IS NOT NULL
            """, (project_id, start_date))
            avg_response_time = cursor.fetchone()[0] or 0
            
            # 场景统计
            cursor.execute("""
                SELECT COUNT(*) FROM test_scenarios WHERE project_id = ?
            """, (project_id,))
            total_scenarios = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT scenario_id) FROM test_executions 
                WHERE project_id = ? AND created_at >= ?
            """, (project_id, start_date))
            active_scenarios = cursor.fetchone()[0]
            
            success_rate = success_count / total_executions if total_executions > 0 else 0
            
            return {
                "total_executions": total_executions,
                "success_count": success_count,
                "failed_count": total_executions - success_count,
                "success_rate": round(success_rate, 4),
                "avg_response_time": round(avg_response_time, 2),
                "total_scenarios": total_scenarios,
                "active_scenarios": active_scenarios
            }
        finally:
            conn.close()
    
    async def get_trend_data(self, project_id: str, metric: str = "success_rate", days: int = 30) -> List[Dict]:
        """
        获取趋势数据
        
        Args:
            project_id: 项目ID
            metric: 指标类型 (success_rate, response_time, execution_count)
            days: 天数
        
        Returns:
            [
                {"date": "2024-01-01", "value": 0.85},
                {"date": "2024-01-02", "value": 0.90},
                ...
            ]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            if metric == "success_rate":
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success
                    FROM test_executions
                    WHERE project_id = ? AND created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (project_id, start_date))
                
                results = []
                for row in cursor.fetchall():
                    date, total, success = row
                    value = success / total if total > 0 else 0
                    results.append({"date": date, "value": round(value, 4)})
                
            elif metric == "response_time":
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        AVG(CAST(json_extract(result, '$.avg_response_time') AS REAL)) as avg_time
                    FROM test_executions
                    WHERE project_id = ? AND created_at >= ? AND result IS NOT NULL
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (project_id, start_date))
                
                results = [{"date": row[0], "value": round(row[1] or 0, 2)} for row in cursor.fetchall()]
                
            elif metric == "execution_count":
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as count
                    FROM test_executions
                    WHERE project_id = ? AND created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (project_id, start_date))
                
                results = [{"date": row[0], "value": row[1]} for row in cursor.fetchall()]
            
            else:
                results = []
            
            return results
        finally:
            conn.close()
    
    async def get_api_stats(self, project_id: str) -> List[Dict]:
        """
        获取各接口的统计数据
        
        Returns:
            [
                {
                    "api_name": "GET /users",
                    "total_executions": 50,
                    "success_count": 45,
                    "failed_count": 5,
                    "success_rate": 0.9,
                    "avg_response_time": 123.4
                },
                ...
            ]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 从test_steps中聚合数据
            cursor.execute("""
                SELECT 
                    ts.name,
                    ts.method,
                    ts.path,
                    COUNT(*) as total,
                    SUM(CASE WHEN te.status = 'success' THEN 1 ELSE 0 END) as success
                FROM test_steps ts
                JOIN test_scenarios tsc ON ts.scenario_id = tsc.id
                JOIN test_executions te ON te.scenario_id = tsc.id
                WHERE tsc.project_id = ?
                GROUP BY ts.name, ts.method, ts.path
                ORDER BY total DESC
                LIMIT 20
            """, (project_id,))
            
            results = []
            for row in cursor.fetchall():
                name, method, path, total, success = row
                api_name = f"{method} {path}" if method and path else name
                success_rate = success / total if total > 0 else 0
                
                results.append({
                    "api_name": api_name,
                    "total_executions": total,
                    "success_count": success,
                    "failed_count": total - success,
                    "success_rate": round(success_rate, 4),
                    "avg_response_time": 0  # TODO: 需要在执行时记录每个步骤的响应时间
                })
            
            return results
        finally:
            conn.close()
    
    async def get_failure_analysis(self, project_id: str, days: int = 7) -> Dict:
        """
        分析失败原因并分类
        
        Returns:
            {
                "failure_categories": [
                    {"category": "断言失败", "count": 15},
                    {"category": "超时", "count": 8},
                    {"category": "连接错误", "count": 5}
                ],
                "recent_failures": [
                    {
                        "scenario_name": "用户登录",
                        "error_message": "断言失败: 期望200, 实际401",
                        "timestamp": "2024-01-01 10:30:00"
                    }
                ]
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # 获取失败的执行记录
            cursor.execute("""
                SELECT 
                    tsc.name,
                    te.result,
                    te.created_at
                FROM test_executions te
                JOIN test_scenarios tsc ON te.scenario_id = tsc.id
                WHERE tsc.project_id = ? AND te.status = 'failed' AND te.created_at >= ?
                ORDER BY te.created_at DESC
                LIMIT 50
            """, (project_id, start_date))
            
            failures = cursor.fetchall()
            
            # 简单的失败分类(基于关键词)
            categories = defaultdict(int)
            recent_failures = []
            
            for scenario_name, result_json, timestamp in failures:
                import json
                try:
                    result = json.loads(result_json) if result_json else {}
                    error_msg = result.get('error', '未知错误')
                except:
                    error_msg = '解析错误'
                
                # 分类
                if '断言' in error_msg or 'assertion' in error_msg.lower():
                    categories['断言失败'] += 1
                elif '超时' in error_msg or 'timeout' in error_msg.lower():
                    categories['超时'] += 1
                elif '连接' in error_msg or 'connection' in error_msg.lower():
                    categories['连接错误'] += 1
                elif '404' in error_msg or '500' in error_msg:
                    categories['HTTP错误'] += 1
                else:
                    categories['其他错误'] += 1
                
                # 最近失败
                if len(recent_failures) < 10:
                    recent_failures.append({
                        "scenario_name": scenario_name,
                        "error_message": error_msg[:100],  # 限制长度
                        "timestamp": timestamp
                    })
            
            failure_categories = [
                {"category": cat, "count": count}
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
            ]
            
            return {
                "failure_categories": failure_categories,
                "recent_failures": recent_failures
            }
        finally:
            conn.close()
    
    async def generate_sankey_data(self, scenario_id: int) -> Dict:
        """
        生成桑基图数据(接口调用链路)
        
        Returns:
            {
                "nodes": [
                    {"name": "开始"},
                    {"name": "GET /login"},
                    {"name": "POST /users"},
                    {"name": "结束"}
                ],
                "links": [
                    {"source": 0, "target": 1, "value": 100},
                    {"source": 1, "target": 2, "value": 95},
                    {"source": 2, "target": 3, "value": 90}
                ]
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取场景的所有步骤
            cursor.execute("""
                SELECT id, name, method, path, step_order
                FROM test_steps
                WHERE scenario_id = ?
                ORDER BY step_order
            """, (scenario_id,))
            
            steps = cursor.fetchall()
            
            # 构建节点
            nodes = [{"name": "开始"}]
            for step in steps:
                step_id, name, method, path, order = step
                node_name = f"{method} {path}" if method and path else name
                nodes.append({"name": node_name})
            nodes.append({"name": "结束"})
            
            # 构建链接(简化版,实际应该基于执行数据)
            links = []
            for i in range(len(nodes) - 1):
                links.append({
                    "source": i,
                    "target": i + 1,
                    "value": 100 - i * 5  # 模拟数据,实际应该从执行记录中统计
                })
            
            return {
                "nodes": nodes,
                "links": links
            }
        finally:
            conn.close()
