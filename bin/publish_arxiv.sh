#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 设置 PYTHONPATH
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

echo "--- 正在启动 arXiv 发布任务 (Publish arXiv) ---"
./env/bin/python src/task/publish_arxiv_task.py
