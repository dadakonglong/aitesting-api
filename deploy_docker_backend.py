import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"
NODE14 = "/opt/node14/bin/node"

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

    # ===== 1. 用 Docker 运行后端（Python 3.11, 完全兼容）=====
    run(c, f"""
docker rm -f aitesting-backend 2>/dev/null || true
docker run -d \
  --name aitesting-backend \
  --restart always \
  -p 8000:8000 \
  -v {TARGET_DIR}/services/ai-processing:/app \
  -w /app \
  -e PYTHONPATH=/app \
  python:3.11-slim \
  bash -c "pip install fastapi uvicorn httpx sqlalchemy==1.4.46 pydantic==1.10.7 python-dotenv python-multipart faker openai langchain langchain-openai langchain-community qdrant-client -q && uvicorn main_sqlite:app --host 0.0.0.0 --port 8000"
echo "Backend container started"
sleep 10
docker logs aitesting-backend --tail 20
""", "Docker 方式运行后端", timeout=120)

    # ===== 2. 验证后端 =====
    run(c, "curl -s -m 5 -o /dev/null -w 'Backend: HTTP %{http_code}' http://localhost:8000/docs", "验证后端 API")

    # ===== 3. 用 Node 14 运行前端 =====
    run(c, f"""
pkill -f "node.*server.js" 2>/dev/null; sleep 1
cd /opt/frontend_standalone/standalone
export PORT=3000
export HOSTNAME=0.0.0.0
nohup {NODE14} server.js > /tmp/frontend.log 2>&1 &
echo "Frontend PID: $!"
sleep 4
cat /tmp/frontend.log
""", "Node 14 启动前端")

    # ===== 4. 设置 Nginx 反向代理（通过 Docker）=====
    run(c, f"""
# 停止并删除旧 nginx 容器
docker rm -f aitesting-nginx 2>/dev/null || true

# 写 Nginx 配置
mkdir -p /opt/nginx_conf
cat > /opt/nginx_conf/aitesting.conf << 'EOF'
server {{
    listen 80;
    server_name _;
    
    location / {{
        proxy_pass http://host-gateway:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
    
    location /api/ {{
        proxy_pass http://host-gateway:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
EOF

# 用宿主机网络模式运行 nginx
docker run -d \
  --name aitesting-nginx \
  --restart always \
  --network host \
  -v /opt/nginx_conf/aitesting.conf:/etc/nginx/conf.d/aitesting.conf:ro \
  nginx:alpine
sleep 3
docker logs aitesting-nginx --tail 10
""", "Docker Nginx 反向代理")

    # ===== 5. 最终验证 =====
    run(c, """
echo "=== Docker 容器 ==="
docker ps --filter 'name=aitesting' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "=== 端口 ==="
ss -tpln | grep -E ':(80|8000|3000) '
echo ""
echo "=== API 验证 ==="
curl -s -m 5 -o /dev/null -w 'Backend: %{http_code}' http://localhost:8000/docs
echo ""
curl -s -m 5 -o /dev/null -w 'Frontend: %{http_code}' http://localhost:3000
echo ""
curl -s -m 5 -o /dev/null -w 'Nginx: %{http_code}' http://localhost:80
echo ""
""", "最终验证", timeout=30)

    print("\n" + "="*60)
    print("  🎉 部署完成！")
    print("  🌐 前端 (无需端口): http://10.0.251.1")
    print("  🔧 后端 API 文档 : http://10.0.251.1:8000/docs")
    print("="*60)
    c.close()

if __name__ == "__main__":
    main()
