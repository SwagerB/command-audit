#!/bin/bash
while true; do
    echo "=========="
    echo "$(date '+%Y-%m-%d %H:%M:%S') 开始刷新"
    python3 /root/audit.py > /dev/null 2>&1
    python3 /root/generate_report.py
    sleep 60
done
