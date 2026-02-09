# DailyPaper

# Contents
- [DailyPaper](#dailypaper)
- [Contents](#contents)
- [Introduction](#introduction)
- [Install](#install)
  - [1. 克隆仓库](#1-克隆仓库)
  - [2. 创建虚拟环境](#2-创建虚拟环境)
- [Usage](#usage)
  - [1. 抓取论文 (run.bash)](#1-抓取论文-runbash)
  - [2. 查询论文 (query.sh)](#2-查询论文-querysh)
  - [3. 标记处理完成 (mark_done.sh)](#3-标记处理完成-mark_donesh)
  - [4. 微信公众号发布 (publish_wechat.sh)](#4-微信公众号发布-publish_wechatsh)
- [n8n 工作流建议](#n8n-工作流建议)

# Introduction

**DailyPaper** 是一个用于**自动抓取、筛选并持久化每日学术论文**的工具。  
它集成了 **本地 Ollama** 的 AI 总结能力，支持将每日论文自动汇总并发布到**微信公众号草稿箱**。

核心特性包括：

- 📄 自动从指定源抓取最新论文
- 🔍 自动去重：数据库仅存储唯一论文，且支持标记处理状态
- 🤖 本地 AI 自动总结：集成 Ollama (如 Qwen2.5) 生成通俗易懂的学术综述
- 📱 微信自动化：支持一键发布到微信公众号草稿箱
- 🗄️ 纯本地化：使用 SQLite 存储，不依赖外部文件或存储服务
- 🕒 遵循 `AGENT.md` 规范，所有可执行文件均在 `bin/` 目录下

---

# Install

## 1. 克隆仓库

```bash
git clone https://github.com/yourname/DailyPaper.git
cd DailyPaper
```

## 2. 创建虚拟环境

项目要求使用 `env` 目录作为虚拟环境。

```bash
python3 -m venv env
./env/bin/pip install -r requirements.txt
```

---

# Usage

## 1. 抓取论文 (run.sh)

用于从远程源同步论文到本地 SQLite 数据库。

```bash
./bin/run.sh
```

- **功能**：抓取最新论文，存入 `data/papers.sqlite3`。
- **注意**：新抓取的论文 `notified` 状态默认为 `0`（未处理）。

## 2. 查询论文 (query.sh)

供 n8n 等工具调用，以 JSON 格式返回论文列表。

```bash
./bin/query.sh [OPTIONS]
```

**常用参数：**
- `--notified [0|1]`：过滤处理状态。`0` 表示未处理，`1` 表示已处理。
- `--limit [N]`：限制返回的论文条数，默认 `10`。
- `--db [PATH]`：指定数据库路径，默认使用 `data/papers.sqlite3`。

**示例：**
```bash
# 查询 20 篇尚未处理的新论文
./bin/query.sh --notified 0 --limit 20
```

## 3. 标记处理完成 (mark_done.sh)

在 n8n 流程执行成功后，调用此脚本将论文标记为已处理。

```bash
./bin/mark_done.sh [IDS...] [--file JSON_FILE]
```

**使用方式：**
- **直接传入 ID**：
  ```bash
  ./bin/mark_done.sh 25870 25871
  ```
- **通过 JSON 文件批量标记**（推荐 n8n 使用）：
  ```bash
  ./bin/mark_done.sh --file ids.json
  ```
  *JSON 文件格式要求：一个包含 ID 整数的数组，或带有 "ids" 键的对象。*

## 4. 微信公众号发布 (publish_wechat.sh)

调用 AI 总结未通知的论文并发布到微信草稿箱。

```bash
./bin/publish_wechat.sh
```

- **配置**：需在 `config/base.yaml` 中配置 `ollama` 和 `wechat` 相关参数。
- **自动触发**：设置环境变量 `ENABLE_WECHAT_PUBLISH=true` 后，运行 `./bin/run.sh` 会在抓取后自动执行此发布任务。

---

# n8n 工作流建议

1. **定时同步**：使用 Cron 节点定时运行 `./bin/run.sh`。
2. **提取数据**：使用 Execute Command 节点运行 `./bin/query.sh --notified 0` 获取 JSON 数据。
3. **业务逻辑**：n8n 处理发送通知、AI 总结等。
4. **状态闭环**：在流程最后，使用 Execute Command 节点运行 `./bin/mark_done.sh` 并传入已处理的 URL，确保下次不再重复查询。

---

> DailyPaper：让每天的论文更新，稳定且精准。
