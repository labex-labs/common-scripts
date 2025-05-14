# 创建 .pystartup 文件并写入内容
cat << 'EOF' > ~/.pystartup
import time
from threading import Thread
import readline
import os

histfile = os.path.join(os.path.expanduser("~"), ".python_history")

def write_history():
    while True:
        time.sleep(3)
        readline.write_history_file(histfile)

background_thread = Thread(target=write_history)
background_thread.daemon = True
background_thread.start()
EOF
# 创建 .python_history 文件（如果不存在）
touch ~/.python_history
# 将 PYTHONSTARTUP 环境变量添加到 .zshrc
echo 'export PYTHONSTARTUP=~/.pystartup' >> ~/.zshrc