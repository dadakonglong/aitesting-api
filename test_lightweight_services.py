"""
测试轻量级知识图谱和向量检索功能
"""

import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'ai-processing'))

from lightweight_services import LightweightKnowledgeGraph, LightweightVectorSearch
import numpy as np

async def test_knowledge_graph():
    """测试知识图谱功能"""
    print("\n" + "="*50)
    print("测试知识图谱功能")
    print("="*50)
    
    kg = LightweightKnowledgeGraph("data/test_kg.pkl")
    
    # 添加API节点
    kg.add_api("api1", path="/user/login", method="POST", name="用户登录")
    kg.add_api("api2", path="/user/profile", method="GET", name="获取用户信息")
    kg.add_api("api3", path="/user/logout", method="POST", name="用户登出")
    
    print(f"✅ 已添加 3 个API节点")
    
    # 添加依赖关系
    kg.add_dependency("api1", "api2", field_mapping={"token": "Authorization"})
    kg.add_dependency("api1", "api3", field_mapping={"token": "Authorization"})
    
    print(f"✅ 已添加 2 条依赖关系")
    
    # 查询依赖
    deps = kg.get_dependencies("api1")
    print(f"\n📊 API1 的依赖关系:")
    for dep in deps:
        print(f"  → {dep['path']} ({dep['method']})")
        print(f"    字段映射: {dep['field_mapping']}")
        print(f"    使用次数: {dep['count']}")
    
    # 统计信息
    stats = kg.get_stats()
    print(f"\n📈 知识图谱统计:")
    print(f"  总API数: {stats['total_apis']}")
    print(f"  总依赖数: {stats['total_dependencies']}")
    print(f"  平均依赖: {stats['avg_dependencies']:.2f}")

def test_vector_search():
    """测试向量检索功能"""
    print("\n" + "="*50)
    print("测试向量检索功能")
    print("="*50)
    
    vs = LightweightVectorSearch("data/test_vectors.db")
    
    # 添加测试向量
    print("📊 添加测试向量...")
    for i in range(5):
        vector = np.random.rand(1536).astype('float32')
        metadata = {
            'path': f'/api/test{i}',
            'method': 'GET',
            'summary': f'测试API {i}'
        }
        vs.add_vector(f"api{i}", vector, metadata)
    
    print(f"✅ 已添加 5 个向量")
    
    # 搜索
    query_vector = np.random.rand(1536).astype('float32')
    results = vs.search(query_vector, k=3, threshold=0.0)
    
    print(f"\n🔍 搜索结果 (Top 3):")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['path']} ({result['method']})")
        print(f"     相似度: {result['score']:.4f}")
    
    # 统计信息
    stats = vs.get_stats()
    print(f"\n📈 向量检索统计:")
    print(f"  总向量数: {stats['total_vectors']}")
    print(f"  数据库记录: {stats['db_records']}")
    print(f"  向量维度: {stats['dimension']}")
    
    vs.close()

async def main():
    """主测试函数"""
    print("\n🚀 开始测试轻量级知识图谱和向量检索功能\n")
    
    try:
        # 测试知识图谱
        await test_knowledge_graph()
        
        # 测试向量检索
        test_vector_search()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过!")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
