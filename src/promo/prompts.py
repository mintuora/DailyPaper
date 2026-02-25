from dataclasses import dataclass


@dataclass(frozen=True)
class Prompts:
    paper_interpretation: str
    paper_interpretation_format: str
    chinese_title: str
    chinese_abstract: str

    @classmethod
    def from_dict(cls, data: dict):
        data = data or {}
        paper_interpretation = (data.get("paper_interpretation") or "").strip()
        paper_interpretation_format = (data.get("paper_interpretation_format") or "").strip()
        chinese_title = (data.get("chinese_title") or "").strip()
        chinese_abstract = (data.get("chinese_abstract") or "").strip()

        missing = []
        if not paper_interpretation:
            missing.append("prompts.paper_interpretation")
        if not paper_interpretation_format:
            missing.append("prompts.paper_interpretation_format")
        if not chinese_title:
            missing.append("prompts.chinese_title")
        if not chinese_abstract:
            missing.append("prompts.chinese_abstract")
        if missing:
            raise ValueError("缺少必要 prompts 配置: " + ", ".join(missing))

        return cls(
            paper_interpretation=paper_interpretation,
            paper_interpretation_format=paper_interpretation_format,
            chinese_title=chinese_title,
            chinese_abstract=chinese_abstract,
        )

