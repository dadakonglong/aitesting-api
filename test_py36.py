import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"
TARGET_DIR = "/opt/aitesting-api"

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

    # 1. 尝试使用 Python 3.6 创建 venv
    run(c, f"""
cd {TARGET_DIR}/services/ai-processing
rm -rf venv_36
python3 -m venv venv_36
./venv_36/bin/pip install --upgrade pip -q
# 安装 Python 3.6 兼容的最后版本
./venv_36/bin/pip install "fastapi<0.70.0" "uvicorn<0.16.0" "pydantic<1.10.0" "sqlalchemy<1.5.0" "httpx<0.20.0" python-dotenv python-multipart faker -q
echo "基础依赖安装完成"
./venv_36/bin/python -c "import fastapi; print('FastAPI version:', fastapi.__version__)"
""", "构建 Python 3.6 兼容环境")

    # 2. 检查代码语法兼容性
    run(c, f"""
cd {TARGET_DIR}/services/ai-processing
./venv_36/bin/python -m py_compile main_sqlite.py || echo "语法不支持"
""", "语法检查")

    c.close()

if __name__ == "__main__":
    main()
