import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"

# 使用 DaoCloud 镜像地址，通常这个比较稳
PYTHON_IMG = "docker.m.daocloud.io/library/python:3.11-slim"
NGINX_IMG  = "docker.m.daocloud.io/library/nginx:alpine"
NODE_IMG   = "docker.m.daocloud.io/library/node:18-alpine"

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

    # 1. 再次确认清理代理
    run(c, """
rm -rf /etc/systemd/system/docker.service.d/*
systemctl daemon-reload
systemctl restart docker
sleep 3
""", "清理代理并重启 Docker")

    # 2. 拉取镜像
    for img in [PYTHON_IMG, NGINX_IMG, NODE_IMG]:
        run(c, f"docker pull {img}", f"拉取 {img}", timeout=300)

    # 3. 部署启动
    run(c, f"""
# 后端
docker rm -f aitesting-backend 2>/dev/null || true
docker run -d \
  --name aitesting-backend \
  --restart always \
  -p 8000:8000 \
  -v {TARGET_DIR}/services/ai-processing:/app \
  -w /app \
  {PYTHON_IMG} \
  bash -c "pip install fastapi uvicorn httpx sqlalchemy pydantic python-dotenv python-multipart openai langchain langchain-openai langchain-community qdrant-client -q && uvicorn main_sqlite:app --host 0.0.0.0 --port 8000"

# 前端
docker rm -f aitesting-frontend 2>/dev/null || true
docker run -d \
  --name aitesting-frontend \
  --restart always \
  -p 3000:3000 \
  -v /opt/frontend_standalone/standalone:/app \
  -e PORT=3000 -e HOSTNAME=0.0.0.0 \
  {NODE_IMG} \
  node /app/server.js

# Nginx
docker rm -f aitesting-nginx 2>/dev/null || true
docker run -d \
  --name aitesting-nginx \
  --restart always \
  --network host \
  -v /opt/nginx_conf/prod.conf:/etc/nginx/conf.d/default.conf:ro \
  {NGINX_IMG}
""", "部署启动容器", timeout=60)

    print("\n⏳ 等待后端初始化...")
    time.sleep(15)
    run(c, "docker logs aitesting-backend --tail 5", "查看后端日志")

    # 4. 验证
    run(c, """
echo "=== 容器列表 ==="
docker ps --filter 'name=aitesting'
echo ""
echo "=== 端口验证 ==="
curl -I http://localhost:8000/docs
curl -I http://localhost:3000
curl -I http://localhost:80
""", "最终验证", timeout=30)

    print("\n✅ 部署完成！")
    c.close()

if __name__ == "__main__":
    main()
