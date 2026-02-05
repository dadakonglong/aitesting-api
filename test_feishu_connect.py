
import asyncio
import httpx
import sys

async def test_connect():
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/8a56a00a-7904-4e44-bfc5-6db55c370c43"
    print(f"Testing connection to: {url}")
    try:
        print("Attempting with trust_env=False (ignoring system proxies)...")
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.post(url, json={"msg_type": "text", "content": {"text": "test"}})
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform =="win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_connect())
