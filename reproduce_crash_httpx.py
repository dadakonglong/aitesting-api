import httpx
import asyncio
import traceback

async def test():
    url = "http://httpbin.org/get"
    # Simulating what is in the DB: List of dicts describing parameters
    # but httpx expects key-value pairs.
    params_schema = [{"name": "ktvid", "in": "query", "type": "string"}]
    
    print(f"Testing httpx with params={params_schema}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params_schema)
            print("Status:", resp.status_code)
            print("URL:", resp.url)
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
