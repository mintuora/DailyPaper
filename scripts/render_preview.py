import os
from jinja2 import Environment, FileSystemLoader


def main():
    template_path = "data/assets/paper_template.html"
    template_dir = os.path.dirname(template_path) or "."
    template_name = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    template = env.get_template(template_name)

    related_papers = [
        {
            "chinese_title": "保持性权衡：边际收益递减阶段中的热力学界限（移动端排版预览）",
            "authors_display": "Alisia Verylonglastname, Bob Robertson, Catherine de Something, David E. Example et al.",
            "publish_time": "2026-02-06",
            "doi_url": "https://arxiv.org/pdf/2602.06046",
            "interpretation": "这是一段用于预览的 AI 深度解读，包含一些数学符号：$\\mathbb{R}$、$\\alpha^2$、$\\frac{1}{2}$，以及长段落用于观察换行与行高表现。",
            "chinese_abstract": "摘要预览文本：这段文字用于观察中文摘要在移动端的行距、左右留白以及整体密度是否舒适。建议在手机上重点看 DOI 行是否会撑破布局。",
            "fig1_url": None,
            "title": "The Preservation Tradeoff: A Thermodynamic Bound in the Diminishing-Returns Regime",
            "abstract": "Preview abstract text for mobile rendering. The key check is that the authors and DOI wrap naturally without ellipsis.",
        }
    ]

    popular_papers = [
        {
            "chinese_title": "AIRS-Bench：面向前沿人工智能研究科学智能体的任务套件（长作者+长链接预览）",
            "authors_display": "Author A, Author B, Author C, Author D, Author E, Author F, Author G et al.",
            "publish_time": "2026-02-06",
            "doi_url": "https://doi.org/10.1234/this.is.a.very.long.doi.identifier/with/many/segments/and_even_more_characters",
            "interpretation": "用于预览的解读块，观察标题、徽章、内容块之间的间距是否紧凑。",
            "chinese_abstract": None,
            "fig1_url": None,
            "title": "AIRS-Bench: a Suite of Tasks for Frontier AI Research Science Agents",
            "abstract": "Another preview abstract. This block exists to validate spacing on mobile and desktop widths.",
        }
    ]

    html = template.render(related_papers=related_papers, popular_papers=popular_papers)

    out_dir = "temp/html"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "preview_mobile.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(out_path)


if __name__ == "__main__":
    main()

