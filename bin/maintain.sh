#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 设置 PYTHONPATH
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

PYTHON_BIN="$PROJECT_DIR/env/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

DB_PATH=$($PYTHON_BIN -c "import yaml; print(yaml.safe_load(open('config/base.yaml'))['db_path'])")

echo "--- 正在启动维护任务 (Maintain) ---"
./env/bin/python src/task/maintain_task.py

# 仍然保留日志清理的 bash 逻辑，因为 find 命令更高效
LOG_DIR="log"
if [ -d "$LOG_DIR" ]; then
    echo "正在清理 7 天前的日志文件..."
    find "$LOG_DIR" -name "*.log" -mtime +7 -exec rm {} \;
    echo "日志清理完成。"
fi

# 清理临时文件 (PDF, 图片, HTML调试文件等)
TEMP_DIR="temp"
if [ -d "$TEMP_DIR" ]; then
    echo "正在清理临时文件夹: $TEMP_DIR"
    rm -rf "$TEMP_DIR"/*
    echo "临时文件夹已清空。"
fi

# PDF_DIR=$($PYTHON_BIN -c "import yaml; print(yaml.safe_load(open('config/base.yaml')).get('pdf_dir', 'data/pdfs'))")
# if [ -d "$PDF_DIR" ]; then
#     echo "正在清理 PDF 存储目录: $PDF_DIR"
#     rm -rf "$PDF_DIR"/*
#     echo "PDF 目录已清空。"
# fi

