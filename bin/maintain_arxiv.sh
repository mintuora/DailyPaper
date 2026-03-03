#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 设置 PYTHONPATH
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

echo "--- 正在启动 arXiv 维护任务 (Maintain arXiv) ---"
./env/bin/python src/task/maintain_arxiv_task.py

# 保留日志清理
LOG_DIR="log"
if [ -d "$LOG_DIR" ]; then
    echo "正在清理 7 天前的日志文件..."
    find "$LOG_DIR" -name "*.log" -mtime +7 -exec rm {} \;
    echo "日志清理完成。"
fi

# 清理临时文件
TEMP_DIR="temp"
if [ -d "$TEMP_DIR" ]; then
    echo "正在清理临时文件夹: $TEMP_DIR"
    rm -rf "$TEMP_DIR"/*
    echo "临时文件夹已清空。"
fi
