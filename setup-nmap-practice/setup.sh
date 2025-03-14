#!/bin/bash

# Check if script is running with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root: sudo $0"
    exit 1
fi

# Update package list and install required tools
apt update -y
apt install -y openssh-server nginx vsftpd bind9 net-tools nmap

# Create necessary directories
mkdir -p /run/sshd /var/run/vsftpd /var/cache/bind

# Configure and start SSH service (port 2222)
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
/usr/sbin/sshd -D &
echo "SSH service started, listening on port 2222"

# Configure and start Nginx Web service (port 8080)
# Ensure port is set only once
sed -i '/listen /d' /etc/nginx/sites-available/default
echo "server { listen 8080; root /var/www/html; index index.html; }" > /etc/nginx/sites-available/default
echo "<html><body><h1>Nmap Practice Server - Port 8080</h1></body></html>" > /var/www/html/index.html
nginx -t && nginx -g "daemon off;" &
echo "Nginx service started, listening on port 8080"

# Configure and start FTP service (port 2121)
echo "listen=YES" > /etc/vsftpd.conf
echo "listen_port=2121" >> /etc/vsftpd.conf
echo "anonymous_enable=YES" >> /etc/vsftpd.conf
echo "local_enable=YES" >> /etc/vsftpd.conf
echo "write_enable=YES" >> /etc/vsftpd.conf
/usr/sbin/vsftpd /etc/vsftpd.conf &
echo "FTP service started, listening on port 2121"

# Configure and start DNS service (port 5353 UDP)
cat <<EOF > /etc/bind/named.conf.options
options {
    directory "/var/cache/bind";
    listen-on port 5353 { 127.0.0.1; 172.17.0.0/16; };
    allow-query { any; };
    listen-on-v6 { none; };
};
EOF
named -g > /var/log/named.log 2>&1 &
echo "DNS service started, listening on port 5353 (UDP), logs redirected to /var/log/named.log"

# Get Docker container IP address
LOCAL_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -n 1)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="172.17.0.2 (please verify manually)"
fi

# Display running services and ports
echo "Services configuration completed! Here are the currently running services and ports:"
echo " - SSH: port 2222 (TCP) - 127.0.0.1 or $LOCAL_IP"
echo " - Nginx: port 8080 (TCP) - 127.0.0.1 or $LOCAL_IP"
echo " - FTP: port 2121 (TCP) - 127.0.0.1 or $LOCAL_IP"
echo " - DNS: port 5353 (UDP) - 127.0.0.1 or $LOCAL_IP"