import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"
NODE14 = "/opt/node14/bin/node"

def get_client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USERNAME, PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)
    return c

def run(client, cmd, desc="", timeout=180):
    if desc: print(f"\n🚀 {desc}")
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
                if line.strip(): print(f"   ERR: {line}")
        if time.time() - start > timeout:
            print("   ⏰ 超时"); break
        time.sleep(0.3)
    while chan.recv_ready():
        for line in chan.recv(4096).decode('utf-8','replace').splitlines():
            if line.strip(): print(f"   {line}")

def main():
    c = get_client()
    print("✅ 已连接\n")

    # ===== 1. 移除 Docker 代理，配置阿里云镜像加速 =====
    run(c, """
# 备份并修改 Docker daemon 配置（移除代理，添加镜像加速）
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://docker.m.daocloud.io",
    "https://dockerhub.timeweb.cloud"
  ]
}
EOF
# 移除代理环境变量（如果有）
mkdir -p /etc/systemd/system/docker.service.d/
cat > /etc/systemd/system/docker.service.d/http-proxy.conf << 'EOF'
[Service]
EOF
systemctl daemon-reload
systemctl restart docker
sleep 3
echo "Docker 重启完成"
docker info | grep -A3 "Registry Mirrors"
""", "配置 Docker 阿里云镜像加速并移除代理", timeout=60)

    # ===== 2. 拉取必要镜像 =====
    run(c, """
echo "拉取 Python 3.11 镜像..."
docker pull python:3.11-slim 2>&1 | tail -5
""", "拉取 Python 镜像", timeout=300)

    run(c, """
echo "拉取 Nginx 镜像..."  
docker pull nginx:alpine 2>&1 | tail -5
""", "拉取 Nginx 镜像", timeout=300)

    run(c, """
echo "拉取 Node 18 镜像..."
docker pull node:18-alpine 2>&1 | tail -5
""", "拉取 Node 18 镜像", timeout=300)

    # ===== 3. 启动后端 =====
    run(c, f"""
docker rm -f aitesting-backend 2>/dev/null || true
docker run -d \
  --name aitesting-backend \
  --restart always \
  -p 8000:8000 \
  -v {TARGET_DIR}/services/ai-processing:/app \
  -w /app \
  python:3.11-slim \
  bash -c "pip install fastapi uvicorn httpx 'sqlalchemy' pydantic python-dotenv python-multipart openai langchain langchain-openai langchain-community qdrant-client -q 2>&1 | tail -3 && uvicorn main_sqlite:app --host 0.0.0.0 --port 8000"
echo "后端容器 ID: $(docker ps -q --filter name=aitesting-backend)"
""", "启动后端容器", timeout=30)

    # ===== 等待后端 =====
    print("\n⏳ 等待后端依赖安装（约 2 分钟）...")
    for i in range(12):
        time.sleep(15)
        c2 = get_client()
        _, o, _ = c2.exec_command("docker logs aitesting-backend 2>&1 | tail -3")
        logs = o.read().decode().strip()
        last = logs.splitlines()[-1] if logs.splitlines() else '...'
        print(f"   [{(i+1)*15}s] {last}")
        if 'Application startup complete' in logs or 'Uvicorn running' in logs:
            print("   ✅ 后端已就绪！")
            c2.close(); break
        c2.close()

    # ===== 4. 启动前端（Node 18 Docker 容器）=====
    run(c, f"""
docker rm -f aitesting-frontend 2>/dev/null || true
docker run -d \
  --name aitesting-frontend \
  --restart always \
  -p 3000:3000 \
  -v /opt/frontend_standalone/standalone:/app \
  -e PORT=3000 \
  -e HOSTNAME=0.0.0.0 \
  node:18-alpine \
  node /app/server.js
sleep 5
docker logs aitesting-frontend --tail 10
""", "启动前端容器", timeout=30)

    # ===== 5. 启动 Nginx =====
    run(c, f"""
mkdir -p /opt/nginx_conf
cat > /opt/nginx_conf/default.conf << 'EOF'
server {{
    listen 80;
    server_name _;
    location / {{
        proxy_pass http://10.0.251.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
    location /api/ {{
        proxy_pass http://10.0.251.1:8000/api/;
        proxy_set_header Host $host;
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
""", "启动 Nginx 反向代理", timeout=30)

    # ===== 6. 最终验证 =====
    run(c, """
echo "=== 容器状态 ==="
docker ps --filter 'name=aitesting' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "=== 端口验证 ==="
curl -s -m 5 -o /dev/null -w 'Backend 8000: HTTP %{http_code}\n' http://localhost:8000/docs
curl -s -m 5 -o /dev/null -w 'Frontend 3000: HTTP %{http_code}\n' http://localhost:3000
curl -s -m 5 -o /dev/null -w 'Nginx 80:      HTTP %{http_code}\n' http://localhost:80
""", "✅ 最终验证", timeout=30)

    print("\n" + "="*50)
    print("  🎉 部署完成！")
    print("  🌐 访问: http://10.0.251.1  (无端口)")
    print("  🔧 API:  http://10.0.251.1:8000/docs")
    print("="*50)
    c.close()

if __name__ == "__main__":
    main()
