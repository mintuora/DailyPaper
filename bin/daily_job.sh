#!/bin/bash

# 获取脚本所在目录的绝对路径，并定位到项目根目录
cd "$(dirname "$0")/.." || exit 1
PROJECT_DIR=$(pwd)

# 日志记录函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== 启动每日论文自动化流水线 ==="

# 确保必要的目录存在
mkdir -p log data data/pdfs temp/html

# 检查环境
if [ ! -d "env" ]; then
    log "❌ 虚拟环境 env 不存在，请先配置环境。"
    exit 1
fi
# 1. 获取任务
log "--- 步骤 1: 获取 (Fetch) ---"
if ./bin/fetch.sh; then
    log "✅ 获取任务成功完成。"
else
    log "❌ 获取任务失败，跳过发布步骤。"
    exit 1
fi

# 2. 发布任务
log "--- 步骤 2: 发布 (Publish) ---"
if ./bin/publish.sh; then
    log "✅ 发布任务成功完成。"
else
    log "❌ 发布任务失败。"
    exit 1
fi

log "=== 每日流水线执行完毕 ==="
