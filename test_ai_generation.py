#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI生成功能
"""
import asyncio
import sys
import os

# 添加路径
sys.path.insert(0, 'services/ai-processing')

from main_sqlite import ai_client

async def test_ai_generation():
    print("=" * 80)
    print("🧪 测试AI生成功能")
    print("=" * 80)
    
    # 测试简单的AI调用
    system_prompt = """你是个测试专家。请返回JSON格式：{"test": "success"}"""
    user_prompt = "测试"
    
    try:
        print("\n📡 调用AI...")
        result = await ai_client.chat(system_prompt, user_prompt)
        print(f"✅ AI响应成功:")
        print(result)
        return True
    except Exception as e:
        print(f"❌ AI调用失败:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        
        # 检查环境变量
        print("\n🔍 检查环境变量:")
        openai_key = os.getenv("OPENAI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        provider = os.getenv("AI_PROVIDER", "openai")
        
        print(f"   AI_PROVIDER: {provider}")
        print(f"   OPENAI_API_KEY: {'已设置' if openai_key else '未设置'}")
        print(f"   DEEPSEEK_API_KEY: {'已设置' if deepseek_key else '未设置'}")
        
        if not openai_key and not deepseek_key:
            print("\n⚠️  未配置任何AI服务的API Key!")
            print("   请在.env文件中配置:")
            print("   OPENAI_API_KEY=your_key")
            print("   或")
            print("   DEEPSEEK_API_KEY=your_key")
            print("   AI_PROVIDER=deepseek")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ai_generation())
    sys.exit(0 if success else 1)
