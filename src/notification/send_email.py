# src/notification/send_email.py
import os
import smtplib
import ssl
import html as _html
from typing import Dict, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate


def _env_or(conf: Dict, key: str, default=None):
    v = os.getenv(key)
    if v is not None and v != "":
        return v
    return conf.get(key, default)


def _safe(s: Optional[str]) -> str:
    return (s or "").strip()


def _escape_html(s: Optional[str]) -> str:
    return _html.escape(_safe(s))


def _truncate(s: str, n: int = 600) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else (s[: n - 1] + "…")


def _pick_abstract(p: Dict) -> str:
    # 兼容不同字段名
    return _safe(p.get("abstract") or p.get("summary") or p.get("abs") or "")


def _build_html_email(
    subject: str,
    summary_line: str,
    relevant_items: List[Dict],
    popular_items: List[Dict],
    max_relevant: int = 30,
    max_popular: int = 5,
) -> str:
    """
    生成适合手机/电脑的 HTML 邮件（简单、兼容大多数客户端）。
    relevant_items / popular_items 的 dict 至少包含:
      title, arxiv_url, publish_time, subject, pdf_views, kimi_calls
    可选:
      abstract / summary / abs
    """

    def item_html(i: int, p: Dict, show_heat: bool = False) -> str:
        title = _escape_html(p.get("title"))
        arxiv = _safe(p.get("arxiv_url"))
        pub = _escape_html(p.get("publish_time"))
        subj = _escape_html(p.get("subject"))
        pdfv = p.get("pdf_views", "")
        kimi = p.get("kimi_calls", "")

        abs_raw = _pick_abstract(p)
        abs_short = _truncate(abs_raw, 70000)
        abs_html = _escape_html(abs_short) if abs_short else ""

        heat = ""
        if show_heat:
            try:
                heat_val = int(p.get("pdf_views") or 0) + int(p.get("kimi_calls") or 0)
                heat = f"<span class='badge'>heat {heat_val}</span>"
            except Exception:
                heat = ""

        abstract_block = f"<div class='abstract'>{abs_html}</div>" if abs_html else ""

        return f"""
        <div class="item">
          <div class="item-title">{i}. <a href="{arxiv}" target="_blank" rel="noopener noreferrer">{title}</a> {heat}</div>
          <div class="meta">
            <span class="pill">{subj or "unknown subject"}</span>
            <span class="muted">publish</span> <span class="mono">{pub or "n/a"}</span>
            &nbsp;·&nbsp;
            <span class="muted">pdf</span> <span class="mono">{pdfv}</span>
            <span class="muted">kimi</span> <span class="mono">{kimi}</span>
          </div>
          {abstract_block}
        </div>
        """

    relevant_html = (
        "".join(
            item_html(i + 1, p) for i, p in enumerate(relevant_items[:max_relevant])
        )
        or "<div class='empty'>(无)</div>"
    )
    popular_html = (
        "".join(
            item_html(i + 1, p, show_heat=True)
            for i, p in enumerate(popular_items[:max_popular])
        )
        or "<div class='empty'>(无)</div>"
    )

    html = f"""\
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape_html(subject)}</title>
  <style>
    body {{ margin:0; padding:0; background:#f6f7fb; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,"Apple Color Emoji","Segoe UI Emoji"; }}
    .wrap {{ max-width: 760px; margin: 0 auto; padding: 16px; }}
    .card {{ background:#ffffff; border:1px solid #e9eaf0; border-radius:14px; padding: 14px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    .title {{ font-size: 18px; font-weight: 700; margin: 0; }}
    .sub {{ margin: 6px 0 0; color:#5b6070; font-size: 13px; line-height: 1.4; }}
    .section {{ margin-top: 14px; }}
    .section h2 {{ font-size: 15px; margin: 0 0 8px; }}
    .item {{ padding: 10px 0; border-top: 1px solid #f0f1f5; }}
    .item:first-child {{ border-top: 0; }}
    .item-title {{ font-size: 14px; font-weight: 600; line-height: 1.35; }}
    a {{ color:#2b6ef2; text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .meta {{ margin-top: 6px; font-size: 12px; color:#5b6070; line-height: 1.4; }}
    .abstract {{ margin-top: 8px; font-size: 13px; color:#2f3440; line-height: 1.55; white-space: pre-wrap; }}
    .pill {{ display:inline-block; padding: 2px 8px; border-radius: 999px; background:#f2f5ff; color:#2b6ef2; font-weight: 600; }}
    .badge {{ display:inline-block; margin-left:6px; padding: 2px 8px; border-radius: 999px; background:#fff4e6; color:#9a5b00; font-weight: 700; font-size: 12px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
    .muted {{ color:#8a90a3; }}
    .empty {{ color:#8a90a3; font-size: 13px; padding: 10px 0; }}
    .footer {{ margin-top: 12px; color:#8a90a3; font-size: 12px; text-align:center; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="header">
        <p class="title">{_escape_html(subject)}</p>
      </div>
      <p class="sub">{_escape_html(summary_line)}</p>

      <div class="section">
        <h2>Relevant</h2>
        {relevant_html}
      </div>

      <div class="section">
        <h2>Popular</h2>
        {popular_html}
      </div>
    </div>

    <div class="footer">
      已附上 CSV 文件（如有）。<br/>
      DailyPaper
    </div>
  </div>
</body>
</html>
"""
    return html


def send_email_smtp(
    mail_conf: Dict,
    subject: str,
    body_text: str,
    *,
    html_body: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> None:
    """
    增强版：
    - 同时发送 plain + html（更好看）
    - 支持附件（CSV 等）
    - CSV 附件名强制为 DailyPaperSum.csv（满足你的需求）

    mail_conf 支持来自 mail.yaml，也支持被环境变量覆盖：
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_TLS
      MAIL_FROM, MAIL_TO
    """
    smtp_host = _env_or(mail_conf, "SMTP_HOST")
    smtp_port = int(_env_or(mail_conf, "SMTP_PORT", 587))
    smtp_user = _env_or(mail_conf, "SMTP_USER")
    smtp_pass = _env_or(mail_conf, "SMTP_PASS")
    smtp_tls = str(_env_or(mail_conf, "SMTP_TLS", "1")).strip() in (
        "1",
        "true",
        "True",
        "yes",
        "YES",
    )

    mail_from = _env_or(mail_conf, "MAIL_FROM", smtp_user)
    mail_to_raw = _env_or(mail_conf, "MAIL_TO")
    if not mail_to_raw:
        raise RuntimeError("MAIL_TO 未配置")
    mail_to = [x.strip() for x in str(mail_to_raw).split(",") if x.strip()]

    if not smtp_host:
        raise RuntimeError("SMTP_HOST 未配置")

    msg = MIMEMultipart("mixed")
    msg["From"] = mail_from
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    if html_body:
        alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    # 附件：CSV 文件名强制改为 DailyPaperSum.csv
    attachments = attachments or []
    csv_renamed = False
    for path in attachments:
        if not path:
            continue
        if not os.path.exists(path):
            continue

        filename = os.path.basename(path)
        if (not csv_renamed) and filename.lower().endswith(".csv"):
            filename = "DailyPaperSum.csv"
            csv_renamed = True

        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)

    context = ssl.create_default_context()

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(mail_from, mail_to, msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if smtp_tls:
                server.starttls(context=context)
                server.ehlo()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(mail_from, mail_to, msg.as_string())


def send_daily_report_email(
    mail_conf: Dict,
    *,
    subject: str,
    summary_line: str,
    relevant_items: List[Dict],
    popular_items: List[Dict],
    attachments: Optional[List[str]] = None,
    max_relevant: int = 30,
    max_popular: int = 5,
) -> None:
    """
    你在 run.py 里推荐调用这个：
    - 自动生成漂亮的 HTML（包含 abstract）
    - 同时生成 plain 文本兜底（包含 abstract）
    - 带附件（CSV 名字会变成 DailyPaperSum.csv）
    """
    lines = [summary_line, ""]
    lines.append("== Relevant ==")
    if not relevant_items:
        lines.append("(无)")
    else:
        for i, p in enumerate(relevant_items[:max_relevant], 1):
            lines.append(f"{i}. {p.get('title')}")
            lines.append(f"   {p.get('arxiv_url')}")
            abs_ = _pick_abstract(p)
            if abs_:
                lines.append("   " + _truncate(abs_, 70000).replace("\n", " "))

    lines.append("")
    lines.append("== Popular ==")
    if not popular_items:
        lines.append("(无)")
    else:
        for i, p in enumerate(popular_items[:max_popular], 1):
            heat = int(p.get("pdf_views") or 0) + int(p.get("kimi_calls") or 0)
            lines.append(f"{i}. heat={heat} {p.get('title')}")
            lines.append(f"   {p.get('arxiv_url')}")
            abs_ = _pick_abstract(p)
            if abs_:
                lines.append("   " + _truncate(abs_, 70000).replace("\n", " "))

    body_text = "\n".join(lines)

    html_body = _build_html_email(
        subject=subject,
        summary_line=summary_line,
        relevant_items=relevant_items,
        popular_items=popular_items,
        max_relevant=max_relevant,
        max_popular=max_popular,
    )

    send_email_smtp(
        mail_conf,
        subject=subject,
        body_text=body_text,
        html_body=html_body,
        attachments=attachments,
    )
