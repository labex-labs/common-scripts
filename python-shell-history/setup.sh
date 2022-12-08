cd ~
wget https://labfile.oss.aliyuncs.com/courses/3946/.pystartup
touch .python_history
echo 'export  PYTHONSTARTUP=~/.pystartup' >> ~/.zshrc
source ~/.zshrc