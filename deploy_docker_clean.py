import paramiko, time, io, os, zipfile

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"

def get_client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USERNAME, PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)
    return c

def run(client, cmd, desc="", timeout=300):
    if desc: print(f"\n{'='*50}\n🚀 {desc}\n{'='*50}")
    transport = client.get_transport()
    chan = transport.open_session()
    chan.exec_command(cmd)
    start = time.time()
    while not chan.exit_status_ready():
        if chan.recv_ready():
            for line in chan.recv(4096).decode('utf-8','replace').splitlines():
                if line.strip(): print(f"   {line}")
        if chan.recv_stderr_ready():
            for line in chan.recv_stderr(4096).decode('utf-8','replace').splitlines():
                if line.strip() and 'WARNING' not in line and 'DeprecationWarning' not in line:
                    print(f"   ⚠️  {line}")
        if time.time() - start > timeout:
            print("   ⏰ 超时，跳过"); break
        time.sleep(0.3)
    while chan.recv_ready():
        for line in chan.recv(4096).decode('utf-8','replace').splitlines():
            if line.strip(): print(f"   {line}")
    return chan.recv_exit_status() if chan.exit_status_ready() else -1

def upload_code(client):
    """打包并上传项目代码"""
    print(f"\n{'='*50}\n📦 打包上传项目代码\n{'='*50}")
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk("."):
            # 排除不必要的大目录
            dirs[:] = [d for d in dirs if d not in [
                'node_modules', '.git', '.next', 'venv', '__pycache__',
                '.gemini', 'antigravity'
            ]]
            for f in files:
                p = os.path.relpath(os.path.join(root, f), ".")
                if any(x in p for x in ['project.zip', '.pyc', 'project_docker.zip']): continue
                z.write(p)
                count += 1
    buf.seek(0)
    size = buf.getbuffer().nbytes / 1024 / 1024
    print(f"   打包完成: {count} 个文件, {size:.1f} MB")
    sftp = client.open_sftp()
    try: sftp.mkdir(TARGET_DIR)
    except: pass
    sftp.putfo(buf, f"{TARGET_DIR}/project.zip")
    sftp.close()
    print("   ✅ 上传完成")

def main():
    print("🚀 开始 Docker 方式部署到 10.0.251.1")
    print("="*50)
    
    c = get_client()
    print("✅ SSH 已连接")

    # ===== 步骤 1：上传代码 =====
    upload_code(c)

    # ===== 步骤 2：解压代码 =====
    run(c, f"""
rm -rf {TARGET_DIR}/services {TARGET_DIR}/frontend
unzip -o {TARGET_DIR}/project.zip -d {TARGET_DIR} 2>&1 | tail -3
echo "解压完成"
ls {TARGET_DIR}/
""", "解压代码")

    # ===== 步骤 3：停止旧容器 =====
    run(c, """
docker rm -f aitesting-backend aitesting-frontend aitesting-nginx 2>/dev/null || true
echo "旧容器已清理"
""", "清理旧容器", timeout=30)

    # ===== 步骤 4：启动后端（Python 3.11 Docker）=====
    # 直接用 docker run，不构建镜像，pip install 在容器内进行
    run(c, f"""
docker run -d \
  --name aitesting-backend \
  --restart always \
  -p 8000:8000 \
  -v {TARGET_DIR}/services/ai-processing:/app \
  -w /app \
  python:3.11-slim \
  bash -c "pip install fastapi uvicorn httpx 'sqlalchemy==2.0.0' pydantic python-dotenv python-multipart openai langchain langchain-openai langchain-community qdrant-client -q 2>&1 | tail -3 && uvicorn main_sqlite:app --host 0.0.0.0 --port 8000 --workers 1"
echo "后端容器启动中..."
""", "启动后端容器", timeout=30)

    # ===== 等待后端依赖安装（首次需要时间）=====
    print("\n⏳ 等待后端依赖安装（最多 3 分钟）...")
    for i in range(18):
        time.sleep(10)
        c2 = get_client()
        _, o, _ = c2.exec_command("docker logs aitesting-backend --tail 5 2>&1")
        logs = o.read().decode()
        print(f"   [{(i+1)*10}s] {logs.strip().splitlines()[-1] if logs.strip() else '...'}")
        if 'Application startup complete' in logs or 'Uvicorn running' in logs:
            print("   ✅ 后端启动成功！")
            c2.close()
            break
        c2.close()

    # ===== 步骤 5：后端 API 验证 =====
    run(c, """
docker ps --filter name=aitesting-backend --format 'Status: {{.Status}}'
curl -s -m 5 -o /dev/null -w 'Backend HTTP: %{http_code}' http://localhost:8000/docs
echo ""
""", "验证后端")

    # ===== 步骤 6：构建并启动前端（Next.js Docker）=====
    # 直接用 standalone 产物 + Node 14（已安装）
    NODE14 = "/opt/node14/bin/node"
    run(c, f"""
ls {NODE14} && {NODE14} --version || echo "Node 14 not found"
# 前端已有 standalone 产物
ls /opt/frontend_standalone/standalone/server.js 2>/dev/null && echo "standalone OK" || echo "Need to rebuild"
""", "检查前端环境")

    # 改用更轻量的方式：直接用 Docker 运行 Node 18 + standalone
    run(c, f"""
docker rm -f aitesting-frontend 2>/dev/null || true
docker run -d \
  --name aitesting-frontend \
  --restart always \
  -p 3000:3000 \
  -v /opt/frontend_standalone/standalone:/app \
  -w /app \
  -e PORT=3000 \
  -e HOSTNAME=0.0.0.0 \
  -e NEXT_PUBLIC_API_URL=http://10.0.251.1:8000 \
  node:18-alpine \
  node server.js
echo "前端容器启动中..."
sleep 5
docker logs aitesting-frontend --tail 10
""", "Docker 启动前端", timeout=60)

    # ===== 步骤 7：Nginx 反向代理 =====
    run(c, f"""
mkdir -p /opt/nginx_conf
cat > /opt/nginx_conf/default.conf << 'EOF'
server {{
    listen 80;
    server_name _;

    # 前端 (Next.js)
    location / {{
        proxy_pass http://10.0.251.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }}

    # 后端 API
    location /api/ {{
        proxy_pass http://10.0.251.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
EOF

docker rm -f aitesting-nginx 2>/dev/null || true
docker run -d \
  --name aitesting-nginx \
  --restart always \
  -p 80:80 \
  -v /opt/nginx_conf/default.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine
sleep 3
docker logs aitesting-nginx --tail 5
""", "启动 Nginx 容器")

    # ===== 步骤 8：最终验证 =====
    time.sleep(5)
    run(c, """
echo "=== 容器状态 ==="
docker ps --filter 'name=aitesting' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "=== API 验证 ==="
curl -s -m 5 -o /dev/null -w 'Backend (8000): HTTP %{http_code}\n' http://localhost:8000/docs
curl -s -m 5 -o /dev/null -w 'Frontend (3000): HTTP %{http_code}\n' http://localhost:3000
curl -s -m 5 -o /dev/null -w 'Nginx (80):      HTTP %{http_code}\n' http://localhost:80
""", "🎯 最终验证", timeout=30)

    print("\n" + "="*50)
    print("  ✅ 部署完成！")
    print("  🌐 前端: http://10.0.251.1  （直接访问，无需端口）")
    print("  🔧 后端: http://10.0.251.1:8000/docs")
    print("="*50)
    c.close()

if __name__ == "__main__":
    main()
