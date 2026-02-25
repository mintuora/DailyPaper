#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

CRON_JOB="0 7 * * * $PROJECT_DIR/bin/daily_job.sh >> $PROJECT_DIR/log/\$(date +\%Y\%m\%d)_cron.log 2>&1"

# 检查是否已经存在该脚本的任务，如果存在则更新，不存在则添加
if crontab -l 2>/dev/null | grep -Fq "$PROJECT_DIR/bin/daily_job.sh"; then
    # 替换现有任务
    (crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/bin/daily_job.sh"; echo "$CRON_JOB") | crontab -
    echo "✅ crontab 任务已更新 (日志现在将按日期保存)。"
else
    # 添加到 crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ 任务已添加到 crontab (每天早上 7:00 执行，日志按日期保存)。"
fi
