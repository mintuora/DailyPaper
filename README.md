# DailyPaper

**DailyPaper** 是一个用于**自动抓取、筛选、AI 解读并发布每日学术论文**的工具。  
当前支持 **arXiv 主链路** 与 **PubMed 独立抓取链路**：
- arXiv：抓取 + 筛选 + AI 解读 + 微信草稿发布（原有 daily_job 主流程）。
- PubMed：独立抓取、独立数据库存储（不污染 arXiv 库）。

---

## 核心特性

- 📄 **多任务架构**：arXiv 与 PubMed 任务解耦，互不影响。
- 🗃️ **独立数据库**：`arxiv_papers.sqlite3` 与 `pubmed_papers.sqlite3` 分离。
- 🔍 **智能筛选**：支持关键词与热度筛选（arXiv 主流程）。
- 🤖 **AI 深度解读**：集成本地 Ollama 生成中文总结。
- 📱 **微信集成**：自动生成 HTML 并推送到公众号草稿箱。
- 🛠️ **自动化调度**：内置 arXiv 日常任务与 crontab 配置。

---

## 使用指南

### 1. arXiv 每日流水线（保持原有）
```bash
bash ./bin/daily_job.sh
```

### 2. 单独任务执行
- **arXiv 抓取**：`bash ./bin/fetch_arxiv.sh`
- **arXiv 发布**：`bash ./bin/publish_arxiv.sh`
- **arXiv 维护**：`bash ./bin/maintain_arxiv.sh`
- **PubMed 抓取（独立）**：`bash ./bin/fetch_pubmed.sh`

### 3. arXiv 定时任务（crontab）
```bash
bash ./bin/setup_cron.sh
```

---

## 数据与目录命名

- arXiv 数据库：`data/arxiv_papers.sqlite3`
- PubMed 数据库：`data/pubmed_papers.sqlite3`
- arXiv PDF 目录：`data/arxiv_pdfs`

---

## 项目结构

- `bin/`: 任务脚本入口（按 arXiv / PubMed 拆分命名）。
- `src/`: 核心源代码（任务、抓取、数据库、AI、发布）。
- `config/`: 配置文件目录。
- `data/`: 数据目录（SQLite、PDF、资源）。
- `log/`: 日志目录。

---

> DailyPaper：让前沿论文追踪更智能、更高效。
