#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查并启动AI服务
"""
import subprocess
import time
import sys
import os

def check_service():
    """检查服务是否运行"""
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def main():
    print("=" * 80)
    print("🔍 检查AI服务状态")
    print("=" * 80)
    
    # 1. 检查服务是否运行
    print("\n📡 检查服务...")
    if check_service():
        print("✅ AI服务正在运行 (http://localhost:8000)")
        print("\n💡 服务正常，如果前端仍然失败，请检查：")
        print("   1. 浏览器控制台的错误信息")
        print("   2. 前端环境变量配置（.env.local）")
        print("   3. CORS配置")
        return 0
    
    print("❌ AI服务未运行")
    
    # 2. 检查环境变量
    print("\n🔧 检查环境变量...")
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    provider = os.getenv("AI_PROVIDER", "openai")
    
    print(f"   AI_PROVIDER: {provider}")
    print(f"   OPENAI_API_KEY: {'✅ 已配置' if openai_key else '❌ 未配置'}")
    print(f"   DEEPSEEK_API_KEY: {'✅ 已配置' if deepseek_key else '❌ 未配置'}")
    
    if not openai_key and not deepseek_key:
        print("\n⚠️  错误: 未配置任何AI服务的API Key")
        print("   请在.env文件中配置:")
        print("   OPENAI_API_KEY=your_key")
        print("   或")
        print("   DEEPSEEK_API_KEY=your_key")
        print("   AI_PROVIDER=deepseek")
        return 1
    
    # 3. 询问是否启动服务
    print("\n🚀 是否启动AI服务？")
    print("   选项:")
    print("   1. 在当前终端启动（会占用终端）")
    print("   2. 在新终端启动（推荐）")
    print("   3. 手动启动（显示命令）")
    print("   4. 退出")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == "1":
        print("\n🚀 启动AI服务...")
        print("   按 Ctrl+C 停止服务")
        print("-" * 80)
        os.chdir("services/ai-processing")
        subprocess.run([sys.executable, "main_sqlite.py"])
    
    elif choice == "2":
        print("\n🚀 在新终端启动AI服务...")
        if sys.platform == "win32":
            subprocess.Popen(
                ["start", "cmd", "/k", f"cd services\\ai-processing && {sys.executable} main_sqlite.py"],
                shell=True
            )
        else:
            subprocess.Popen(
                ["gnome-terminal", "--", "bash", "-c", f"cd services/ai-processing && {sys.executable} main_sqlite.py; exec bash"]
            )
        
        print("✅ 已在新终端启动服务")
        print("\n⏳ 等待服务启动...")
        for i in range(10):
            time.sleep(1)
            if check_service():
                print("✅ 服务启动成功！")
                return 0
            print(f"   等待中... ({i+1}/10)")
        
        print("⚠️  服务可能需要更多时间启动，请检查新终端窗口")
    
    elif choice == "3":
        print("\n📋 手动启动命令:")
        print("-" * 80)
        print("cd services/ai-processing")
        print(f"{sys.executable} main_sqlite.py")
        print("-" * 80)
        print("\n或使用Docker:")
        print("docker-compose up -d ai-service")
    
    else:
        print("\n👋 已退出")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 已停止")
        sys.exit(0)
