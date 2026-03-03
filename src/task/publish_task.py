import os
import yaml
import logging
import time
import random
import fitz
import re
import requests
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from src.db import DBManager
from src.wechat import WeChatPublisher
from src.promo import PaperPromoGenerator
from src.misc.bark_notifier import BarkNotifier
from src.misc.logger import setup_run_logger
from src.ranking import get_top_popular, filter_relevant_by_keywords
from src.misc.config_loader import get_base_conf, get_task_conf
from src.promo.prompts import Prompts

logger = logging.getLogger("DailyPaper")

def download_pdf(url, save_path):
    """下载 PDF 文件"""
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
        return True
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/pdf'}
    try:
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        logger.error(f"下载 PDF 异常: {e}")
    return False

def extract_pdf_content(pdf_path):
    """
    PDF 信息提取：
    1. 提取前 15 页文本 (增加扫描范围)
    2. 多策略提取候选图片：
       - 渲染前 8 页（高清渲染，确保捕获所有关键图表）
       - 搜索包含 "Figure", "Method", "Overview" 等关键词的页面并优先渲染
    3. 不再提取嵌入图片（避免碎片化小图干扰）
    """
    text = ""
    candidate_paths = []
    
    try:
        doc = fitz.open(pdf_path)
        # 1. 提取文本 (前 15 页)
        for page in doc[:15]: 
            text += page.get_text()
        
        os.makedirs("temp/figs", exist_ok=True)
        base_name = os.path.basename(pdf_path).replace(".pdf", "")
        
        # 2. 页面渲染策略 (不再提取嵌入图，只渲染页面)
        found_pages = set()
        
        # 策略 A: 优先渲染前 8 页 (通常核心图表都在前面)
        for i in range(min(8, len(doc))):
            page_path = os.path.join("temp/figs", f"{base_name}_page_{i+1}.png")
            # 2.0 倍高清渲染
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            pix.save(page_path)
            candidate_paths.append(page_path)
            found_pages.add(i)
            
        # 策略 B: 补充搜索关键页面 (如果不在前 8 页)
        keywords = ["Figure 1", "Fig. 1", "Figure 2", "Fig. 2", "Method", "Overview", "Architecture"]
        
        for i, page in enumerate(doc[:15]): # 扫描前 15 页
            if i in found_pages: continue
            
            page_text = page.get_text()
            # 如果包含关键词，也渲染出来
            for kw in keywords:
                if kw in page_text:
                    page_path = os.path.join("temp/figs", f"{base_name}_keypage_{i+1}.png")
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    pix.save(page_path)
                    candidate_paths.append(page_path)
                    found_pages.add(i)
                    break
            
            if len(candidate_paths) >= 12: 
                break
        
        doc.close()
        logger.info(f"PDF 提取完成，生成 {len(candidate_paths)} 张渲染页面")
    except Exception as e:
        logger.error(f"PDF 提取异常: {e}")
        
    return text, candidate_paths

def process_single_paper(p, pdf_dir, publisher, generator, db_path):
    """
    处理单篇论文的并发单元
    返回处理后的 paper_data (包含 interpretation, fig1_url) 或 None (被过滤)
    """
    logger.info(f"正在处理论文: {p['title']}")
    
    # 增加单篇处理的重试机制
    for attempt in range(3):
        try:
            p_copy = p.copy()
            # 1. 标题和摘要翻译
            p_copy['chinese_title'] = generator.get_chinese_title(p['title'])
            p_copy['chinese_abstract'] = generator.get_chinese_abstract(p['abstract'])
            
            # 2. PDF 下载与深度解读
            pdf_url = p['arxiv_url'].replace('abs', 'pdf') + ".pdf"
            pdf_filename = p['arxiv_url'].split('/')[-1] + ".pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            
            pdf_text = ""
            fig1_local_path = None
            interpretation = ""
            is_relevant = True
            
            download_success = download_pdf(pdf_url, pdf_path)
            if download_success:
                pdf_text, candidate_paths = extract_pdf_content(pdf_path)
                # 为每一篇论文生成深度解读，并进行二次判定
                interpretation, is_relevant = generator.get_pdf_interpretation(pdf_text)
                p_copy['interpretation'] = interpretation
                
                if candidate_paths:
                    fig1_local_path = generator.select_best_image(candidate_paths)
                else:
                    fig1_local_path = None
            else:
                logger.warning(f"下载 PDF 失败: {pdf_url}")
                # 如果下载失败，且不是热门文章，默认设为不相关以避免空内容推送
                if not p.get('is_popular', False):
                    is_relevant = False

            is_popular = p.get('is_popular', False)
            logger.info(f"AI 二次判定: {'相关' if is_relevant else '不相关'} (热门: {is_popular}) - {p['title']}")
            
            # 二次判定逻辑：如果不是热门文章，且 AI 认为该文章不符合推送类型
            if not is_popular and not is_relevant:
                logger.warning(f"🚫 AI 二次判定不相关或 PDF 下载失败，跳过并标记为不推送: {p['title']}")
                # 更新数据库状态为 0 (所有)
                db = DBManager(db_path) 
                db.update_status([p['arxiv_url']], 0)
                return None 
            
            if is_popular and not is_relevant:
                if not download_success:
                    logger.warning(f"⚠️ 热门文章 PDF 下载失败，将尝试仅使用摘要信息推送: {p['title']}")
                else:
                    logger.info(f"✅ 虽然 AI 判定不相关，但由于是热门文章，保留推送: {p['title']}")            
            # 3. 图片上传微信
            p_copy['fig1_url'] = None
            if fig1_local_path:
                for img_attempt in range(3):
                    try:
                        img_url = publisher.upload_image(fig1_local_path, is_cover=False)
                        if img_url: 
                            p_copy['fig1_url'] = img_url
                            break
                    except:
                        time.sleep(2)
            
            # 4. 调试：Base64 嵌入 (仅用于本地预览)
            if fig1_local_path and os.path.exists(fig1_local_path):
                try:
                    with open(fig1_local_path, "rb") as img_f:
                        img_data = base64.b64encode(img_f.read()).decode('utf-8')
                        p_copy['fig1_url_debug'] = f"data:image/png;base64,{img_data}"
                except Exception as e:
                    logger.error(f"Base64 转换异常: {e}")
            
            return p_copy
        except Exception as e:
            logger.warning(f"处理论文 {p['title']} 尝试 {attempt+1} 失败: {e}")
            if attempt == 2: return None
            time.sleep(5)
    return None

def run_publish():
    setup_run_logger()
    logger, _ = setup_run_logger(name="DailyPaper")
    logger.info("--- 启动发布任务 (Publish) ---")

    conf = get_base_conf()
    
    db_path = conf.get("db_path", "data/papers.sqlite3")
    pdf_dir = conf.get("pdf_dir", "data/pdfs")
    ollama_conf = conf.get("ollama", {})
    wc_conf = conf.get("wechat", {})
    daily_limit = conf.get("daily_limit", 100)
    
    db = DBManager(db_path)
    
    # 获取待推送论文 (状态 1)
    papers = db.get_unnotified_papers(limit=daily_limit)
    logger.info(f"获取到 {len(papers)} 篇待推送论文")
    if not papers:
        logger.info("没有新的论文需要发布")
        return

    task_conf = get_task_conf() or {}

    keywords = task_conf.get("keyword", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    pending_urls = [p["arxiv_url"] for p in papers if p.get("arxiv_url")]

    top_n = conf.get("top_popular_n", 5)
    popular_papers = get_top_popular(db_path, pending_urls, top_n=top_n)
    popular_urls = {p["arxiv_url"] for p in popular_papers if p.get("arxiv_url")}

    relevant_papers = filter_relevant_by_keywords(db_path, pending_urls, keywords)
    relevant_urls = {p["arxiv_url"] for p in relevant_papers if p.get("arxiv_url")}

    for p in papers:
        url = p.get("arxiv_url")
        p["is_popular"] = bool(url and url in popular_urls)
        p["is_relevant"] = bool(url and url in relevant_urls)

    publisher = WeChatPublisher(wc_conf)
    ollama_options = ollama_conf.get("options", {})
    prompts_conf = Prompts.from_dict(conf.get("prompts", {}))
    generator = PaperPromoGenerator(
        ollama_conf.get("base_url"),
        ollama_conf.get("model"),
        prompts_conf,
        template_path="data/assets/paper_template.html",
        ollama_options=ollama_options,
        vl_model=ollama_conf.get("vl_model"),
        vl_options=ollama_conf.get("vl_options"),
    )

    # 1. 并发处理所有论文 (获取数据，但不生成 HTML)
    valid_papers = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_single_paper, p, pdf_dir, publisher, generator, db_path) for p in papers]
        for future in futures:
            try:
                p_data = future.result()
                if p_data:
                    valid_papers.append(p_data)
            except Exception as e:
                logger.error(f"处理论文失败: {e}")

    if not valid_papers:
        logger.info("经过 AI 判定，无符合条件的论文推送")
        return

    processed_arxiv_urls = [p.get("arxiv_url") for p in valid_papers if p.get("arxiv_url")]

    popular_valid = [p for p in valid_papers if p.get("is_popular")]
    related_valid = [p for p in valid_papers if p.get("is_relevant") and not p.get("is_popular")]
    other_valid = [p for p in valid_papers if not p.get("is_relevant") and not p.get("is_popular")]
    if other_valid:
        related_valid.extend(other_valid)

    related_debug = []
    for p in related_valid:
        p_debug = p.copy()
        p_debug["fig1_url"] = p.get("fig1_url_debug") if p.get("fig1_url_debug") else None
        related_debug.append(p_debug)

    popular_debug = []
    for p in popular_valid:
        p_debug = p.copy()
        p_debug["fig1_url"] = p.get("fig1_url_debug") if p.get("fig1_url_debug") else None
        popular_debug.append(p_debug)

    full_article_html = generator.render_full_article(related_valid, popular_valid)
    full_article_html_debug = generator.render_full_article(related_debug, popular_debug)
    
    # 保存调试版
    debug_html_dir = "temp/html"
    os.makedirs(debug_html_dir, exist_ok=True)
    with open(os.path.join(debug_html_dir, "full_article.html"), "w", encoding="utf-8") as f:
        f.write(full_article_html_debug)

    # 4. 发布逻辑
    try:
        display_date = datetime.now().strftime('%Y-%m-%d')
        summary_article = {
            "title": f"ai4protein论文推荐 | {display_date}",
            "author": wc_conf.get("author", "DailyPaper"),
            "summary": f"今日共 {len(processed_arxiv_urls)} 篇论文等待您查收。",
            "content": full_article_html,
            "cover_image": wc_conf.get("cover_path")
        }

        # 增加微信 API 重试
        res = None
        for i in range(3):
            try:
                res = publisher.publish_article(summary_article, draft=True)
                if res and res.get("media_id"): break
            except Exception as e:
                logger.warning(f"微信发布尝试 {i+1} 失败: {e}")
                time.sleep(5)
        
        summary_media_id = res.get("media_id") if res else None
        if summary_media_id:
            logger.info(f"✅ 汇总文章草稿保存成功: {summary_media_id}")
            db.mark_notified(processed_arxiv_urls)
            notifier = BarkNotifier(conf.get("bark", {}).get("api_key"))
            notifier.send("微信草稿保存成功", summary_article["title"])
        else:
            logger.error("微信草稿保存失败，状态未更新。")
    except Exception as e:
        logger.error(f"汇总文章草稿异常: {e}")

if __name__ == "__main__":
    run_publish()
