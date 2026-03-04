import paramiko, time

HOST = "10.0.251.1"; PORT = 22; USERNAME = "root"; PASSWORD = "123456"

def get_client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, PORT, USERNAME, PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)
    return c

def run(client, cmd, timeout=60):
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
            break
        time.sleep(0.3)
    while chan.recv_ready():
        for line in chan.recv(4096).decode('utf-8','replace').splitlines():
            if line.strip(): print(f"   {line}")

def main():
    c = get_client()
    print("✅ 已连接\n")
    
    print("--- docker ps -a ---")
    run(c, "docker ps -a | grep aitesting")
    
    print("\n--- 手动运行 docker run (带输出) ---")
    run(c, """
docker rm -f aitesting-backend-test 2>/dev/null || true
docker run --name aitesting-backend-test \
  -p 8000:8000 \
  -v /opt/aitesting-api/services/ai-processing:/app \
  -w /app \
  python:3.11-slim \
  echo "DOCKER OK - container started successfully" 2>&1
echo "Exit code: $?"
""", timeout=120)
    
    print("\n--- 检查 docker 报错 ---")
    run(c, "docker info | head -5; docker images | head -5")
    
    c.close()

if __name__ == "__main__":
    main()
