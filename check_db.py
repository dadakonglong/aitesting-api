import sqlite3

conn = sqlite3.connect('data/apis.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM apis')
print(f'API总数量: {c.fetchone()[0]}')

c.execute("SELECT COUNT(*) FROM apis WHERE project_id='default-project'")
print(f'default-project的API数量: {c.fetchone()[0]}')

c.execute('SELECT DISTINCT project_id FROM apis')
projects = [row[0] for row in c.fetchall()]
print(f'项目列表: {projects}')

for project in projects:
    c.execute('SELECT COUNT(*) FROM apis WHERE project_id=?', (project,))
    count = c.fetchone()[0]
    print(f'  {project}: {count}个API')

conn.close()
