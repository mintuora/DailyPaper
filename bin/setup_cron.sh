#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 保持原有 arXiv daily_job 调度不变
CRON_JOB="0 7 * * * $PROJECT_DIR/bin/daily_job.sh >> $PROJECT_DIR/log/\$(date +\%Y\%m\%d)_cron.log 2>&1"

# 检查是否已经存在该脚本的任务，如果存在则更新，不存在则添加
if crontab -l 2>/dev/null | grep -Fq "$PROJECT_DIR/bin/daily_job.sh"; then
    (crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/bin/daily_job.sh"; echo "$CRON_JOB") | crontab -
    echo "✅ arXiv crontab 任务已更新。"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ arXiv crontab 任务已添加。"
fi
