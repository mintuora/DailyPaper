# DailyPaper
# Contents
- [DailyPaper](#dailypaper)
- [Contents](#contents)
- [Introduction](#introduction)
- [Install](#install)
  - [1. 克隆仓库](#1-克隆仓库)
  - [2. 创建 Python 环境（推荐）](#2-创建-python-环境推荐)
  - [3. 安装依赖](#3-安装依赖)
- [Usage](#usage)
  - [1. 配置邮件参数](#1-配置邮件参数)
  - [2. 运行 DailyPaper](#2-运行-dailypaper)
  - [3. 定时运行（示例）](#3-定时运行示例)
- [Thanks](#thanks)

# Introduction

**DailyPaper** 是一个用于**自动抓取、筛选并汇总每日学术论文**的工具，主要面向 arXiv 等公开论文源。  
它支持根据自定义规则筛选 *Relevant* 与 *Popular* 论文，并自动生成 **CSV 汇总文件** 与 **HTML/Plain 双格式邮件**，每日定时推送到指定邮箱。

核心特性包括：

- 📄 自动抓取最新论文（按 `updated_at` / `published_at`）
- 🔍 可定制的论文筛选逻辑（Relevant / Popular）
- 📊 热度统计（PDF views + Kimi calls）
- ✉️ 自动发送结构化 HTML 邮件（含 abstract）
- 📎 自动附加汇总文件 `DailyPaperSum.csv`
- 🕒 适合配合 cron / systemd 定时运行

---

# Install

## 1. 克隆仓库

```bash
git clone https://github.com/yourname/DailyPaper.git
cd DailyPaper
````

## 2. 创建 Python 环境（推荐）

```bash
conda create -n dailypaper python=3.10
conda activate dailypaper
```

或使用 `venv`：

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. 安装依赖

```bash
pip install -r requirements.txt
```

---

# Usage

## 1. 配置邮件参数

可通过 `mail.yaml` 或环境变量配置 SMTP（**环境变量优先生效**）：

```yaml
SMTP_HOST: smtp.example.com
SMTP_PORT: 587
SMTP_USER: your@email.com
SMTP_PASS: your_smtp_password
SMTP_TLS: 1
MAIL_FROM: your@email.com
MAIL_TO: a@xx.com,b@yy.com
```

或使用环境变量：

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=your@email.com
export SMTP_PASS=xxxxxx
export SMTP_TLS=1
export MAIL_FROM=your@email.com
export MAIL_TO=a@xx.com,b@yy.com
```

---

## 2. 运行 DailyPaper

```bash
python src/run.py
```

运行后将完成以下步骤：

1. 抓取当日论文数据
2. 筛选 Relevant / Popular 论文
3. 生成 `DailyPaperSum.csv`
4. 发送包含 abstract 的 HTML 邮件

---

## 3. 定时运行（示例）

使用 `cron` 每天 UTC 08:00 执行：

```bash
crontab -e
```

```cron
0 8 * * * cd /path/to/DailyPaper && /path/to/python src/run.py >> daily.log 2>&1
```

---

# Thanks

* chatgpt
* https://kexue.fm/
---

> DailyPaper：让每天的论文更新，像订阅新闻一样简单 📬
