# DailyPaper

**DailyPaper** 是一个用于**自动抓取、筛选、AI 解读并发布每日学术论文**的工具。  
它集成了 **本地 Ollama** 的 AI 能力，支持自动抓取 arXiv 论文，进行关键词和热度筛选，生成深度中文解读，并自动发布到**微信公众号草稿箱**。

---

## 核心特性

- 📄 **自动抓取**：从 arXiv 等源自动同步最新论文。
- 🔍 **智能筛选**：支持基于关键词（Keywords）和热度（Popularity）的双重筛选机制。
- 🤖 **AI 深度解读**：集成本地 Ollama (如 Qwen3) 生成约 500 字的深度中文总结。
- 🎯 **灵活过滤**：热门文章自动保留，普通文章经过 AI 二次判定相关性，确保推送质量。
- 📱 **微信集成**：一键生成美观的 HTML 文章并保存至微信公众号草稿箱。
- 🛠️ **自动化流水线**：内置每日任务脚本，支持系统 crontab 定时调度。

---

## 安装说明

### 1. 克隆仓库
```bash
git clone https://github.com/yourname/DailyPaper.git
cd DailyPaper
```

### 2. 创建虚拟环境
项目要求使用 `env` 目录作为虚拟环境。
```bash
python3 -m venv env
./env/bin/pip install -r requirements.txt
```

### 3. 配置
修改 `config/base.yaml` 中的配置项：
- `db_path`: 数据库路径。
- `ollama`: 配置本地 Ollama 的 URL 和模型。
- `wechat`: 配置公众号的 `app_id` 和 `app_secret`。
- `keywords`: 在 `config/task.yaml`（或相关配置）中设置感兴趣的关键词。

---

## 使用指南

### 1. 每日自动化流水线 (推荐)
运行封装好的流水线脚本，它会自动执行抓取和发布任务：
```bash
bash ./bin/daily_job.sh
```
- **步骤 1 (Fetch)**：抓取论文并根据关键词/热度标记待推送。
- **步骤 2 (Publish)**：执行 AI 解读、图片处理并保存至微信草稿箱。

### 2. 单独任务执行
- **抓取论文**：`bash ./bin/fetch.sh`
- **发布任务**：`bash ./bin/publish.sh`
- **缓存清理**：`bash ./bin/maintain.sh` (仅在需要清空数据库或缓存时手动运行)

### 3. 系统定时任务 (Crontab)
使用内置脚本一键配置每天早上 7:00 自动运行，日志将按日期保存于 `log/` 目录下（例如 `20260225_cron.log`）：
```bash
bash ./bin/setup_cron.sh
```

---

## 项目结构
- `bin/`: 所有可执行脚本入口。
- `src/`: 核心源代码（抓取、数据库、AI 生成、微信发布等）。
- `config/`: 配置文件目录。
- `data/`: 存储 SQLite 数据库、PDF 及资源文件。
- `log/`: 任务执行日志。

---

> DailyPaper：让前沿论文追踪更智能、更高效。
