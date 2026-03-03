import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("DailyPaper")


class PubMedScraper:
    """Fetch latest PubMed papers via NCBI E-utilities API."""

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(
        self,
        timeout: int = 30,
        email: Optional[str] = None,
        tool: str = "DailyPaper",
        api_key: Optional[str] = None,
    ):
        self.timeout = int(timeout)
        self.email = (email or "").strip() or None
        self.tool = (tool or "DailyPaper").strip()
        self.api_key = (api_key or "").strip() or None

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DailyPaper/1.0 (+https://pubmed.ncbi.nlm.nih.gov/)",
                "Accept": "application/json, application/xml;q=0.9, */*;q=0.8",
            }
        )

    def fetch_papers(self, query: str, retmax: int = 50, days_back: int = 1) -> List[Dict]:
        query = (query or "").strip()
        if not query:
            raise ValueError("PubMed query 不能为空")

        pmids = self._search_pmids(query=query, retmax=retmax, days_back=days_back)
        if not pmids:
            return []

        papers: List[Dict] = []
        chunk_size = 200
        for i in range(0, len(pmids), chunk_size):
            chunk = pmids[i : i + chunk_size]
            papers.extend(self._fetch_details(chunk))

        deduped: Dict[str, Dict] = {}
        for p in papers:
            pmid = (p.get("pmid") or "").strip()
            if pmid:
                deduped[pmid] = p
        return list(deduped.values())

    def _base_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if self.tool:
            params["tool"] = self.tool
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _search_pmids(self, query: str, retmax: int, days_back: int) -> List[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "sort": "pub_date",
            "retmode": "json",
            "retmax": max(1, int(retmax or 1)),
            "datetype": "pdat",
            "reldate": max(1, int(days_back or 1)),
        }
        params.update(self._base_params())

        logger.info(
            "PubMed 检索: query=%s, days_back=%s, retmax=%s",
            query,
            params["reldate"],
            params["retmax"],
        )

        response = self.session.get(self.ESEARCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        payload = response.json() or {}
        id_list = (
            payload.get("esearchresult", {}).get("idlist", [])
            if isinstance(payload, dict)
            else []
        )
        return [str(x).strip() for x in id_list if str(x).strip()]

    def _fetch_details(self, pmids: List[str]) -> List[Dict]:
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        params.update(self._base_params())

        response = self.session.get(self.EFETCH_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        return self._parse_pubmed_xml(response.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict]:
        if not xml_text.strip():
            return []

        root = ET.fromstring(xml_text)
        papers: List[Dict] = []

        for node in root.findall(".//PubmedArticle"):
            pmid = self._text(node, "./MedlineCitation/PMID")
            if not pmid:
                continue

            pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            title = self._normalize_ws(
                self._collect_text(node.find("./MedlineCitation/Article/ArticleTitle"))
            )
            abstract = self._extract_abstract(node)
            authors = self._extract_authors(node)
            journal = self._normalize_ws(
                self._text(node, "./MedlineCitation/Article/Journal/Title")
            )
            publish_time = self._extract_publish_date(node)

            doi = self._extract_doi(node)
            doi_url = f"https://doi.org/{doi}" if doi else None

            pmc_id = self._extract_article_id(node, "pmc")
            pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/" if pmc_id else None

            papers.append(
                {
                    "source": "pubmed",
                    "pmid": pmid,
                    "external_id": pmid,
                    "pubmed_url": pubmed_url,
                    "arxiv_url": pubmed_url,
                    "doi": doi_url,
                    "pmc_id": pmc_id or None,
                    "pdf_url": pdf_url,
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "subject": journal,
                    "publish_time": publish_time,
                    "pdf_views": 0,
                    "kimi_calls": 0,
                }
            )

        return papers

    @staticmethod
    def _collect_text(node: Optional[ET.Element]) -> str:
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    @staticmethod
    def _normalize_ws(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def _text(self, parent: ET.Element, path: str) -> str:
        el = parent.find(path)
        if el is None:
            return ""
        return self._normalize_ws("".join(el.itertext()))

    def _extract_authors(self, node: ET.Element) -> List[str]:
        authors: List[str] = []
        for author in node.findall("./MedlineCitation/Article/AuthorList/Author"):
            collective = self._text(author, "./CollectiveName")
            if collective:
                authors.append(collective)
                continue

            last_name = self._text(author, "./LastName")
            fore_name = self._text(author, "./ForeName")
            full_name = " ".join([x for x in [fore_name, last_name] if x]).strip()
            if full_name:
                authors.append(full_name)
        return authors

    def _extract_abstract(self, node: ET.Element) -> Optional[str]:
        texts: List[str] = []
        for abs_node in node.findall("./MedlineCitation/Article/Abstract/AbstractText"):
            label = self._normalize_ws(abs_node.attrib.get("Label", ""))
            content = self._normalize_ws(self._collect_text(abs_node))
            if not content:
                continue
            texts.append(f"{label}: {content}" if label else content)

        if not texts:
            return None
        return "\n".join(texts)

    def _extract_doi(self, node: ET.Element) -> str:
        doi = self._extract_article_id(node, "doi")
        if doi:
            return doi

        for el in node.findall("./MedlineCitation/Article/ELocationID"):
            e_type = (el.attrib.get("EIdType") or "").strip().lower()
            if e_type == "doi":
                text = self._normalize_ws("".join(el.itertext()))
                if text:
                    return text
        return ""

    def _extract_article_id(self, node: ET.Element, id_type: str) -> str:
        expected = (id_type or "").strip().lower()
        for aid in node.findall("./PubmedData/ArticleIdList/ArticleId"):
            actual = (aid.attrib.get("IdType") or "").strip().lower()
            if actual == expected:
                text = self._normalize_ws("".join(aid.itertext()))
                if text:
                    return text
        return ""

    def _extract_publish_date(self, node: ET.Element) -> str:
        # 1) 优先 JournalIssue/PubDate，和每日发表口径一致
        pub_date = node.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate")
        if pub_date is not None:
            y = self._text(pub_date, "./Year")
            m = self._normalize_month(self._text(pub_date, "./Month"))
            d = self._normalize_day(self._text(pub_date, "./Day")) or "01"
            if y and m:
                return f"{y}-{m}-{d}"

            medline_date = self._text(pub_date, "./MedlineDate")
            if medline_date:
                year_match = re.search(r"(19|20)\d{2}", medline_date)
                if year_match:
                    return f"{year_match.group(0)}-01-01"

        # 2) 其次 ArticleDate
        article_date = node.find("./MedlineCitation/Article/ArticleDate")
        if article_date is not None:
            y = self._text(article_date, "./Year")
            m = self._normalize_month(self._text(article_date, "./Month"))
            d = self._normalize_day(self._text(article_date, "./Day"))
            if y and m and d:
                return f"{y}-{m}-{d}"

        # 3) 再次 PubmedData/History 的 pubmed 时间
        for hist in node.findall("./PubmedData/History/PubMedPubDate"):
            status = (hist.attrib.get("PubStatus") or "").strip().lower()
            if status == "pubmed":
                y = self._text(hist, "./Year")
                m = self._normalize_month(self._text(hist, "./Month"))
                d = self._normalize_day(self._text(hist, "./Day"))
                if y and m and d:
                    return f"{y}-{m}-{d}"

        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _normalize_day(day_text: str) -> str:
        digits = re.sub(r"\D", "", day_text or "")
        if not digits:
            return ""
        try:
            day = int(digits)
            if 1 <= day <= 31:
                return f"{day:02d}"
        except ValueError:
            return ""
        return ""

    @staticmethod
    def _normalize_month(month_text: str) -> str:
        value = (month_text or "").strip()
        if not value:
            return ""

        digits = re.sub(r"\D", "", value)
        if digits:
            try:
                month = int(digits)
                if 1 <= month <= 12:
                    return f"{month:02d}"
            except ValueError:
                pass

        month_map = {
            "jan": "01",
            "january": "01",
            "feb": "02",
            "february": "02",
            "mar": "03",
            "march": "03",
            "apr": "04",
            "april": "04",
            "may": "05",
            "jun": "06",
            "june": "06",
            "jul": "07",
            "july": "07",
            "aug": "08",
            "august": "08",
            "sep": "09",
            "sept": "09",
            "september": "09",
            "oct": "10",
            "october": "10",
            "nov": "11",
            "november": "11",
            "dec": "12",
            "december": "12",
        }
        return month_map.get(value.lower(), "")
