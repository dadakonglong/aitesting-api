import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_project_lifecycle():
    # 1. 创建项目
    print("🚀 测试创建项目...")
    project_data = {
        "name": "自动化测试项目",
        "description": "这是一个由测试脚本创建的项目"
    }
    response = requests.post(f"{BASE_URL}/projects", json=project_data)
    if response.status_code == 200:
        data = response.json()
        project_id = data.get("project_id")
        print(f"✅ 项目创建成功! ID: {project_id}")
    else:
        print(f"❌ 项目创建失败: {response.text}")
        return

    # 2. 获取列表
    print("\n🚀 测试获取项目列表...")
    response = requests.get(f"{BASE_URL}/projects")
    if response.status_code == 200:
        projects = response.json()
        print(f"✅ 获取到 {len(projects)} 个项目")
        found = any(p['id'] == project_id for p in projects)
        if found:
            print(f"✅ 在列表中找到了新创建的项目")
        else:
            print(f"❌ 列表中未找到新项目")
    else:
        print(f"❌ 获取列表失败: {response.text}")

    # 3. 删除项目
    print(f"\n🚀 测试删除项目 {project_id}...")
    response = requests.delete(f"{BASE_URL}/projects/{project_id}")
    if response.status_code == 200:
        print(f"✅ 项目删除成功!")
    else:
        print(f"❌ 项目删除失败: {response.text}")

if __name__ == "__main__":
    test_project_lifecycle()
