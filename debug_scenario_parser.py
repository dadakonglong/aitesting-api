
import asyncio
import os
import json
from services.ai_processing.services.scenario_parser import ScenarioParser
from dotenv import load_dotenv

# Load env to get OpenAI Key
load_dotenv(r"d:\testc\aitesting-api\.env")

DB_PATH = r"d:\testc\aitesting-api\data\apis.db"
PROJECT_ID = "default-project"

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found")
        return

    parser = ScenarioParser(api_key=api_key)
    
    # Mock NLU Result (Login scenario)
    nlu_result = {
        "intent": "用户使用手机号登录",
        "actions": [{"name": "login", "type": "api", "target": "user"}]
    }

    print(f"--- Testing Scenario Parser with DB: {DB_PATH} ---")
    try:
        result = await parser.parse_scenario(
            nlu_result=nlu_result,
            project_id=PROJECT_ID,
            db_path=DB_PATH
        )
        
        print("\n--- Parse Result ---")
        steps = result.get("steps", [])
        print(f"Steps generated: {len(steps)}")
        
        for i, step in enumerate(steps):
            print(f"\nStep {i+1}: {step.get('api_method')} {step.get('api_path')}")
            print(f"  API ID: {step.get('api_id')}")
            
            # Check for injected schemas
            params_schema = step.get("params_schema")
            body_schema = step.get("body_schema")
            
            if params_schema:
                print(f"  [OK] Injected Params Schema: Found ({len(params_schema)} items)")
                # print(json.dumps(params_schema, indent=2, ensure_ascii=False))
            else:
                print("  [FAIL] Params Schema: MISSING")
                
            if body_schema:
                print(f"  [OK] Injected Body Schema: Found")
                # print(json.dumps(body_schema, indent=2, ensure_ascii=False))
            else:
                print("  [FAIL] Body Schema: MISSING")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
