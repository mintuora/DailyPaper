#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 设置 PYTHONPATH
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

echo "--- 正在启动获取任务 (Fetch) ---"
./env/bin/python src/task/fetch_task.py
