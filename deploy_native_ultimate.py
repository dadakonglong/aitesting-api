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
                if line.strip() and 'DeprecationWarning' not in line: print(f"   ERR: {line}")
        if time.time() - start > timeout:
            print("   ⏰ 超时"); break
        time.sleep(0.3)
    while chan.recv_ready():
        for line in chan.recv(4096).decode('utf-8','replace').splitlines():
            if line.strip(): print(f"   {line}")

def main():
    c = get_client()
    print("✅ 已连接\n")

    # 1. 彻底停止所有相关进程和容器
    run(c, """
pkill -f uvicorn 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
docker rm -f aitesting-backend aitesting-frontend aitesting-nginx 2>/dev/null || true
echo "已清理所有旧进程和容器"
""", "清理环境")

    # 2. 后端：使用 Python 3.6.8 (系统自带/pyenv) 构建环境
    # 使用阿里云 PyPI 镜像源，极其重要
    run(c, f"""
cd {TARGET_DIR}/services/ai-processing
rm -rf venv_native
python3 -m venv venv_native
./venv_native/bin/pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ -q
./venv_native/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ \
    "fastapi<0.70.0" "uvicorn<0.16.0" "pydantic<1.10.0" "sqlalchemy<1.5.0" "httpx<0.20.0" \
    python-dotenv python-multipart faker openai langchain langchain-openai langchain-community qdrant-client -q
echo "=== 后端依赖安装完成 (Native 3.6.8) ==="
""", "构建后端 Native 环境", timeout=400)

    # 3. 启动后端
    run(c, f"""
cd {TARGET_DIR}/services/ai-processing
export PYTHONPATH={TARGET_DIR}/services/ai-processing
nohup ./venv_native/bin/uvicorn main_sqlite:app --host 0.0.0.0 --port 8000 > /tmp/native_backend.log 2>&1 &
echo "Backend PID: $!"
sleep 5
tail -n 20 /tmp/native_backend.log
""", "启动后端服务")

    # 4. 前端：使用 Node 14 启动 standalone
    run(c, f"""
cd /opt/frontend_standalone/standalone
export PORT=3000
export HOSTNAME=0.0.0.0
nohup {NODE14} server.js > /tmp/native_frontend.log 2>&1 &
echo "Frontend PID: $!"
sleep 5
tail -n 20 /tmp/native_frontend.log
""", "启动前端服务")

    # 5. 最终验证
    run(c, """
echo "=== 进程状态 ==="
ps -ef | grep -E 'uvicorn|node|server.js' | grep -v grep
echo ""
echo "=== 端口状态 ==="
ss -tpln | grep -E ':(8000|3000) '
echo ""
echo "=== HTTP 验证 ==="
curl -s -m 5 -o /dev/null -w 'Backend  (8000): HTTP %{http_code}\n' http://localhost:8000/docs
curl -s -m 5 -o /dev/null -w 'Frontend (3000): HTTP %{http_code}\n' http://localhost:3000
""", "部署结果验证")

    print("\n" + "="*50)
    print("  🎉 部署成功（Native 模式）！")
    print("  🌐 前端入口: http://10.0.251.1:3000")
    print("  🔧 后端 API:  http://10.0.251.1:8000/docs")
    print("  ⚠️  注意: 由于 Nginx 容器无法拉取，目前请直接通过端口访问")
    print("="*50)
    c.close()

if __name__ == "__main__":
    main()
