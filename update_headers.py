import sqlite3
import json

conn = sqlite3.connect('data/apis.db')
c = conn.cursor()

# 获取场景18的测试用例
c.execute('SELECT test_case_id FROM scenarios WHERE id = 18')
tid = c.fetchone()[0]

# 获取步骤
c.execute('SELECT steps FROM test_cases WHERE id = ?', (tid,))
steps = json.loads(c.fetchone()[0])

# 更新第2步的 headers
steps[1]['headers'] = {'Content-Type': 'application/x-www-form-urlencoded'}

# 保存回数据库
c.execute('UPDATE test_cases SET steps = ? WHERE id = ?', (json.dumps(steps, ensure_ascii=False), tid))
conn.commit()

print('✅ 已更新场景步骤的 headers')
print(f'步骤2的 headers: {steps[1]["headers"]}')

conn.close()
