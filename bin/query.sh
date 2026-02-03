#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 设置 PYTHONPATH
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

# 使用项目本地的虚拟环境运行查询脚本
./env/bin/python src/query_api.py "$@"
