#!/bin/bash

# 环境变量
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export TZ='Asia/Shanghai'

# 加载审计命令记录
source /root/audit_setup.sh

# 启动 HTTP 服务（如果没在跑）
if ! pgrep -f "http.server 8000" > /dev/null; then
    cd /root/audit_logs/reports
    nohup python3 -m http.server 8000 --bind 0.0.0.0 \
      > /root/audit_logs/http_server.log 2>&1 &
    echo "HTTP 服务已启动"
fi

# 启动自动刷新（如果没在跑）
if ! pgrep -f "auto_refresh.sh" > /dev/null; then
    nohup /root/auto_refresh.sh \
      > /root/audit_logs/auto_refresh.log 2>&1 &
    echo "自动刷新已启动"
fi

echo "审计系统就绪"