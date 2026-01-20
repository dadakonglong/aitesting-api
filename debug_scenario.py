import sqlite3
import json

conn = sqlite3.connect('data/apis.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 获取最新的场景
c.execute('SELECT id, name, test_case_id FROM scenarios ORDER BY id DESC LIMIT 1')
scenario = c.fetchone()
print(f"场景: {scenario['name']} (ID: {scenario['id']})")
print(f"test_case_id: {scenario['test_case_id']}")

# 获取测试用例步骤
c.execute('SELECT steps FROM test_cases WHERE id = ?', (scenario['test_case_id'],))
tc = c.fetchone()
steps = json.loads(tc['steps'])

print(f"\n总步骤数: {len(steps)}")

# 找到 /vod/song/order 步骤
for step in steps:
    if 'song/order' in step.get('api_path', ''):
        print("\n" + "="*60)
        print(f"步骤 {step.get('step_order')}: {step.get('api_method')} {step.get('api_path')}")
        print("="*60)
        print(f"\ndescription: {step.get('description')}")
        print(f"\nparams (请求体):")
        print(json.dumps(step.get('params', {}), ensure_ascii=False, indent=2))
        print(f"\nurl_params (URL参数):")
        print(json.dumps(step.get('url_params', []), ensure_ascii=False, indent=2))
        print(f"\nheaders:")
        print(json.dumps(step.get('headers', {}), ensure_ascii=False, indent=2))
        print(f"\nparam_mappings (参数映射):")
        print(json.dumps(step.get('param_mappings', []), ensure_ascii=False, indent=2))

# 同时查看 API 定义
print("\n" + "="*60)
print("API 定义对比")
print("="*60)
c.execute('SELECT * FROM apis WHERE path = "/vod/song/order"')
api = c.fetchone()
if api:
    print(f"\nmethod: {api['method']}")
    print(f"\nparameters:")
    print(json.dumps(json.loads(api['parameters'] or '[]'), ensure_ascii=False, indent=2))
    print(f"\nrequest_body:")
    print(json.dumps(json.loads(api['request_body'] or '{}'), ensure_ascii=False, indent=2))

conn.close()
