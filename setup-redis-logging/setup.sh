#!/bin/bash

# Script must be run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with root privileges: sudo $0"
    exit 1
fi

# Define variables
LOG_DIR="/var/log/redis"
LOG_FILE="$LOG_DIR/redis_command_history.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Step 1: Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed, installing now..."
    apt-get update
    apt-get install -y redis-server
    if [ $? -ne 0 ]; then
        echo "Redis installation failed, please check network or package manager configuration."
        exit 1
    fi
else
    echo "Redis is already installed, skipping installation."
fi

# Step 2: Replace redis-cli with a logging wrapper script
echo "Replacing redis-cli with a logging-enabled wrapper script..."
if [ -f "/usr/bin/redis-cli" ]; then
    mv /usr/bin/redis-cli /usr/bin/redis-cli-original
fi

# Create the wrapper script for redis-cli
cat << 'EOF' > /usr/bin/redis-cli
#!/bin/bash
LOG_DIR="/var/log/redis"
LOG_FILE="$LOG_DIR/redis_command_history.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    touch "$LOG_FILE"
    chown labex:labex "$LOG_FILE"  # Owner: labex, Group: labex
    chmod 666 "$LOG_FILE"          # rw-rw-rw- permissions for all users
    echo "[$TIMESTAMP] Redis command history log created." >> "$LOG_FILE"
fi
if [ -t 0 ]; then
    TEMP_FILE="/tmp/redis_session_$$.log"
    /usr/bin/script -q -c "/usr/bin/redis-cli-original" "$TEMP_FILE"
    grep -v '^OK\|^"\|^([integer]' "$TEMP_FILE" | grep -v '^$' | while read -r line; do
        echo "[$TIMESTAMP] $line" >> "$LOG_FILE"
    done
    rm -f "$TEMP_FILE"
else
    echo "[$TIMESTAMP] $@" >> "$LOG_FILE"
    /usr/bin/redis-cli-original "$@"
fi
EOF

chmod +x /usr/bin/redis-cli
echo "redis-cli wrapper script created successfully."

# Step 3: Create log file and set permissions
echo "Creating log file and setting broad read/write permissions..."
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi
touch "$LOG_FILE"
# Set ownership to labex user and group
chown labex:labex "$LOG_FILE"
# Set permissions to 666 (read/write for all)
chmod 666 "$LOG_FILE"
echo "[$TIMESTAMP] Redis command history log created by setup script." >> "$LOG_FILE"

# Ensure the log directory is accessible
chmod 755 "$LOG_DIR"

echo "Configuration completed!"
echo "Users mái now use redis-cli normally, and all commands will be logged to $LOG_FILE."
echo "The labex user and all other users have read/write access to the log file."