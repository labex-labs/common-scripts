#!/bin/bash

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
    echo "请以 root 权限运行此脚本：sudo $0"
    exit 1
fi

# 更新软件包列表并安装必要工具
apt update -y
apt install -y openssh-server nginx vsftpd bind9 net-tools nmap

# 创建必要的目录
mkdir -p /run/sshd /var/run/vsftpd /var/cache/bind

# 配置和启动 SSH 服务 (端口 2222)
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
/usr/sbin/sshd -D &
echo "SSH 服务已启动，监听端口 2222"

# 配置和启动 Nginx Web 服务 (端口 8080)
# 确保端口只设置一次
sed -i '/listen /d' /etc/nginx/sites-available/default
echo "server { listen 8080; root /var/www/html; index index.html; }" > /etc/nginx/sites-available/default
echo "<html><body><h1>Nmap Practice Server - Port 8080</h1></body></html>" > /var/www/html/index.html
nginx -t && nginx -g "daemon off;" &
echo "Nginx 服务已启动，监听端口 8080"

# 配置和启动 FTP 服务 (端口 2121)
echo "listen=YES" > /etc/vsftpd.conf
echo "listen_port=2121" >> /etc/vsftpd.conf
echo "anonymous_enable=YES" >> /etc/vsftpd.conf
echo "local_enable=YES" >> /etc/vsftpd.conf
echo "write_enable=YES" >> /etc/vsftpd.conf
/usr/sbin/vsftpd /etc/vsftpd.conf &
echo "FTP 服务已启动，监听端口 2121"

# 配置和启动 DNS 服务 (端口 5353 UDP)
cat <<EOF > /etc/bind/named.conf.options
options {
    directory "/var/cache/bind";
    listen-on port 5353 { 127.0.0.1; 172.17.0.0/16; };
    allow-query { any; };
    listen-on-v6 { none; };
};
EOF
named -g > /var/log/named.log 2>&1 &
echo "DNS 服务已启动，监听端口 5353 (UDP)，日志已重定向到 /var/log/named.log"

# 获取 Docker 容器的 IP 地址
LOCAL_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v "127.0.0.1" | head -n 1)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="172.17.0.2 (请手动确认)"
fi

# 显示开放的服务和端口
echo "服务配置完成！以下是当前运行的服务和端口："
echo " - SSH: 端口 2222 (TCP) - 127.0.0.1 或 $LOCAL_IP"
echo " - Nginx: 端口 8080 (TCP) - 127.0.0.1 或 $LOCAL_IP"
echo " - FTP: 端口 2121 (TCP) - 127.0.0.1 或 $LOCAL_IP"
echo " - DNS: 端口 5353 (UDP) - 127.0.0.1 或 $LOCAL_IP"
echo "请在容器终端中使用 Nmap 扫描 127.0.0.1 或 $LOCAL_IP 进行实践！"
