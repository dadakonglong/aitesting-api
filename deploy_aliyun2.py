import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"

# 直接使用阿里云完整镜像名，不依赖 tag alias
PYTHON_IMG = "registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim"
NGINX_IMG  = "registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine"
NODE_IMG   = "registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine"

def get_client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USERNAME, PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)
    return c

def run(client, cmd, desc="", timeout=300):
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

    # 确认镜像存在
    run(c, "docker images | head -20", "当前已有镜像")

    # 启动后端（使用完整阿里云镜像名）
    run(c, f"""
docker rm -f aitesting-backend 2>/dev/null || true
docker run -d \
  --name aitesting-backend \
  --restart always \
  -p 8000:8000 \
  -v {TARGET_DIR}/services/ai-processing:/app \
  -w /app \
  {PYTHON_IMG} \
  bash -c "pip install fastapi uvicorn httpx sqlalchemy pydantic python-dotenv python-multipart openai langchain langchain-openai langchain-community qdrant-client -q && uvicorn main_sqlite:app --host 0.0.0.0 --port 8000"
echo "容器 ID: $(docker ps -q --filter name=aitesting-backend)"
""", "启动后端容器", timeout=30)

    print("\n⏳ 等待后端 pip install 完成（约 2.5 分钟）...")
    for i in range(20):
        time.sleep(15)
        c2 = get_client()
        _, o, _ = c2.exec_command("docker logs aitesting-backend 2>&1 | tail -3")
        logs = o.read().decode().strip()
        last = logs.splitlines()[-1] if logs.splitlines() else '...'
        print(f"   [{(i+1)*15}s] {last}")
        if 'Application startup complete' in logs or 'Uvicorn running' in logs:
            print("   ✅ 后端就绪！"); c2.close(); break
        if 'No such container' in last:
            print("   ❌ 容器不存在，查看 docker 日志...")
            _, o2, e2 = c2.exec_command(f"docker run --rm {PYTHON_IMG} python --version 2>&1")
            print(f"   测试: {o2.read().decode().strip()}")
        c2.close()

    # 启动前端
    run(c, f"""
docker rm -f aitesting-frontend 2>/dev/null || true
docker run -d \
  --name aitesting-frontend \
  --restart always \
  -p 3000:3000 \
  -v /opt/frontend_standalone/standalone:/app \
  -e PORT=3000 \
  -e HOSTNAME=0.0.0.0 \
  {NODE_IMG} \
  node /app/server.js
sleep 5
docker logs aitesting-frontend --tail 5
""", "启动前端容器", timeout=30)

    # 启动 Nginx
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
  {NGINX_IMG}
sleep 3
docker logs aitesting-nginx --tail 3
""", "启动 Nginx")

    # 验证
    run(c, """
echo "=== 容器状态 ==="
docker ps --filter 'name=aitesting' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "=== 接口验证 ==="
curl -s -m 5 -o /dev/null -w 'Backend  8000: HTTP %{http_code}\n' http://localhost:8000/docs
curl -s -m 5 -o /dev/null -w 'Frontend 3000: HTTP %{http_code}\n' http://localhost:3000
curl -s -m 5 -o /dev/null -w 'Nginx      80: HTTP %{http_code}\n' http://localhost:80
""", "最终验证", timeout=30)

    print("\n🎉 完成！")
    print("   前端: http://10.0.251.1")
    print("   后端: http://10.0.251.1:8000/docs")
    c.close()

if __name__ == "__main__":
    main()
