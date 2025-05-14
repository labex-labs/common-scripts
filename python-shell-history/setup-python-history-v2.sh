# 创建脚本文件
cat << 'EOF' > setup_python_history.sh
#!/bin/bash

# 创建 .pystartup 文件
cat << 'PYSTARTUP' > ~/.pystartup
# ~/.pystartup
# Python startup script to manage command history
# Saves command history to ~/.python_history on exit
# Supports Linux, macOS, and Windows

import readline
import os
import atexit
import platform

# Determine history file path
if platform.system() == "Windows":
    histfile = os.path.join(os.getenv("USERPROFILE"), ".python_history")
else:
    histfile = os.path.join(os.path.expanduser("~"), ".python_history")

try:
    # Initialize history file
    if not os.path.exists(histfile):
        open(histfile, 'a').close()
        if platform.system() != "Windows":
            os.chmod(histfile, 0o600)
    
    # Load history
    readline.read_history_file(histfile)
except Exception as e:
    print(f"Failed to initialize history file: {e}")

# Set history length
readline.set_history_length(1000)

# Save history
def save_history():
    try:
        readline.write_history_file(histfile)
    except Exception as e:
        print(f"Error saving history: {e}")

atexit.register(save_history)
PYSTARTUP

# 创建 .python_history 文件
if [ ! -f ~/.python_history ]; then
    touch ~/.python_history
    if [[ $(uname) != "Windows" ]]; then
        chmod 600 ~/.python_history
    fi
fi

# 检测壳类型并选择配置文件
if [[ $SHELL == */zsh ]]; then
    rcfile=~/.zshrc
elif [[ $SHELL == */bash ]]; then
    rcfile=~/.bashrc
else
    rcfile=~/.profile
fi

# 检查是否已设置 PYTHONSTARTUP
if ! grep -q "PYTHONSTARTUP" "$rcfile"; then
    echo 'export PYTHONSTARTUP=~/.pystartup' >> "$rcfile"
    echo "Added PYTHONSTARTUP to $rcfile"
else
    echo "PYTHONSTARTUP already set in $rcfile"
fi

# 刷新配置
source "$rcfile" || echo "Failed to source $rcfile"
EOF

# 赋予脚本执行权限
chmod +x setup_python_history.sh