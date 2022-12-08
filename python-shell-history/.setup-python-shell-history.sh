cd ~
wget https://cdn.jsdelivr.net/gh/labex-labs/common-scripts@master/python-shell-history/.pystartup
touch .python_history
echo 'export  PYTHONSTARTUP=~/.pystartup' >> ~/.zshrc
source ~/.zshrc
