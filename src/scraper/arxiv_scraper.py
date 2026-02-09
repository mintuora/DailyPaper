import requests
import lxml.html as LH
import logging
import re
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("DailyPaper")


class ArxivScraper:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def fetch_papers(self, web_url: str) -> List[Dict]:
        logger.info(f"正在抓取网页: {web_url}")
        r = requests.get(web_url, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()

        root = LH.fromstring(r.text)
        container = self._select_main_container(root)
        blocks = container.xpath("./div[./h2]") or container.xpath(".//div[./h2]")

        papers = []
        for b in blocks:
            title = (b.xpath("normalize-space(./h2/a[2])") or "").strip()
            if not title:
                continue

            arxiv_data = b.xpath("./h2/a[3]/@data")
            if not arxiv_data:
                continue
            arxiv_url = arxiv_data[0].strip()

            authors_text = (b.xpath("normalize-space(./p[1])") or "").strip()
            authors = [a.strip() for a in authors_text.split(",")] if authors_text else []

            abstract = (b.xpath("normalize-space(./p[2])") or "").strip() or None
            subject = (b.xpath("normalize-space(./p[3]/span)") or "").strip() or None

            publish_time_text = (b.xpath("normalize-space(./p[4]/span)") or "").strip()
            if publish_time_text:
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", publish_time_text)
                if date_match:
                    publish_time_text = date_match.group(0)
            else:
                publish_time_text = datetime.now().strftime("%Y-%m-%d")

            papers.append(
                {
                    "title": title,
                    "arxiv_url": arxiv_url,
                    "authors": authors,
                    "abstract": abstract,
                    "subject": subject,
                    "pdf_views": 0,
                    "kimi_calls": 0,
                    "publish_time": publish_time_text,
                }
            )
        return papers

    def _select_main_container(self, root) -> LH.HtmlElement:
        body_divs = root.xpath("/html/body/div")
        if not body_divs:
            raise RuntimeError("HTML 结构异常")
        return max(body_divs, key=lambda d: len(d.xpath(".//h2")))
