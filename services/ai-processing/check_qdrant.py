"""
Qdrant 服务诊断脚本
用于检查 Qdrant 向量数据库的连接状态
"""
import os
import sys
import requests
from urllib.parse import urlparse

def check_qdrant_connection(qdrant_url: str):
    """检查 Qdrant 服务连接"""
    print(f"\n{'='*60}")
    print(f"Qdrant 服务诊断")
    print(f"{'='*60}\n")
    
    print(f"配置的 Qdrant URL: {qdrant_url}\n")
    
    # 解析 URL
    try:
        parsed = urlparse(qdrant_url)
        host = parsed.hostname
        port = parsed.port or 6333
        scheme = parsed.scheme or "http"
        
        print(f"解析结果:")
        print(f"  - 协议: {scheme}")
        print(f"  - 主机: {host}")
        print(f"  - 端口: {port}\n")
        
        # 检查是否是 Docker 容器名
        if host == "qdrant":
            print("⚠️  警告: 检测到使用 Docker 容器名 'qdrant'")
            print("   如果不在 Docker 环境中运行，应使用 'localhost' 或 '127.0.0.1'\n")
        
    except Exception as e:
        print(f"❌ URL 解析失败: {e}\n")
        return False
    
    # 测试 HTTP 连接
    health_url = f"{scheme}://{host}:{port}/health"
    collections_url = f"{scheme}://{host}:{port}/collections"
    
    print("1. 检查服务健康状态...")
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ 服务健康检查通过")
            print(f"   响应: {response.json()}")
        else:
            print(f"   ❌ 健康检查失败: HTTP {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 无法连接到 {host}:{port}")
        print(f"   可能原因:")
        print(f"     - Qdrant 服务未启动")
        print(f"     - 端口 {port} 未开放")
        print(f"     - 防火墙阻止连接")
        if host == "qdrant":
            print(f"     - 使用了 Docker 容器名但不在 Docker 网络中")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ 连接超时")
        return False
    except Exception as e:
        print(f"   ❌ 连接错误: {e}")
        return False
    
    print("\n2. 检查 API 端点...")
    try:
        response = requests.get(collections_url, timeout=5)
        if response.status_code == 200:
            print(f"   ✅ API 端点可访问")
            collections = response.json().get("result", {}).get("collections", [])
            print(f"   当前集合数量: {len(collections)}")
            if collections:
                print(f"   集合列表: {[c.get('name') for c in collections]}")
        else:
            print(f"   ⚠️  API 端点返回: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  API 端点检查失败: {e}")
    
    print("\n3. 测试 QdrantClient 连接...")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=qdrant_url, check_compatibility=False)
        collections = client.get_collections()
        print(f"   ✅ QdrantClient 连接成功")
        print(f"   集合数量: {len(collections.collections)}")
        return True
    except ImportError:
        print(f"   ⚠️  qdrant-client 库未安装")
        print(f"   请运行: pip install qdrant-client")
        return False
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ QdrantClient 连接失败")
        print(f"   错误: {error_msg}")
        if "404" in error_msg or "Not Found" in error_msg:
            print(f"\n   💡 解决方案:")
            print(f"      - 如果使用 Docker: docker-compose up -d qdrant")
            print(f"      - 如果本地运行: 确保 Qdrant 在端口 {port} 运行")
            print(f"      - 检查环境变量 QDRANT_URL 是否正确")
        return False
    
    print(f"\n{'='*60}")
    print(f"✅ 所有检查通过！Qdrant 服务运行正常")
    print(f"{'='*60}\n")
    return True

if __name__ == "__main__":
    # 从环境变量获取 URL
    qdrant_url = os.getenv("QDRANT_URL")
    
    if not qdrant_url:
        print("❌ 未设置 QDRANT_URL 环境变量")
        print("\n请设置环境变量:")
        print("  - Windows: set QDRANT_URL=http://localhost:6333")
        print("  - Linux/Mac: export QDRANT_URL=http://localhost:6333")
        print("\n或者直接在命令行指定:")
        print("  python check_qdrant.py http://localhost:6333")
        sys.exit(1)
    
    # 如果命令行提供了 URL，使用命令行参数
    if len(sys.argv) > 1:
        qdrant_url = sys.argv[1]
    
    success = check_qdrant_connection(qdrant_url)
    sys.exit(0 if success else 1)
