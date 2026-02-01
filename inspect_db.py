
import sqlite3
import json

db_path = r"d:\testc\aitesting-api\test_platform.db"

def inspect_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- Latest Scenario ---")
    cursor.execute("SELECT id, name, parsed_structure FROM scenarios ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row['id']}")
        print(f"Name: {row['name']}")
        try:
            structure = json.loads(row['parsed_structure'])
            steps = structure.get('steps', [])
            print(f"Steps count: {len(steps)}")
            for i, step in enumerate(steps):
                print(f"  Step {i+1}: {step.get('api_method')} {step.get('api_path')}")
                print(f"    Params Schema: {json.dumps(step.get('params', 'MISSING'), ensure_ascii=False)}")
        except Exception as e:
            print(f"Error parsing structure: {e}")
    else:
        print("No scenarios found.")

    print("\n--- Latest Test Case ---")
    cursor.execute("SELECT id, name, steps FROM test_cases ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row['id']}")
        print(f"Name: {row['name']}")
        try:
            steps = json.loads(row['steps'])
            print(f"Steps count: {len(steps)}")
            for i, step in enumerate(steps):
                print(f"  Step {i+1}: {step.get('api_method')} {step.get('api_path')}")
                print(f"    Params: {json.dumps(step.get('params', 'MISSING'), ensure_ascii=False)}")
        except Exception as e:
            print(f"Error parsing steps: {e}")
    else:
        print("No test cases found.")

    conn.close()

if __name__ == "__main__":
    inspect_db()
