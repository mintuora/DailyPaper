import logging
import os
import re
import json
import base64
from src.llm import OllamaAPI
from jinja2 import Environment, FileSystemLoader
from pylatexenc.latex2text import LatexNodes2Text
from .prompts import Prompts

logger = logging.getLogger("DailyPaper")


from PIL import Image
import io

class PaperPromoGenerator:
    def __init__(
        self,
        ollama_url,
        ollama_model,
        prompts: Prompts,
        template_path=None,
        ollama_options=None,
        vl_model=None,
        vl_options=None,
    ):
        self.client = OllamaAPI(ollama_url, ollama_model)
        self.prompts = prompts
        self.ollama_options = ollama_options or {}
        self.template_path = template_path
        self.vl_model = vl_model
        self.vl_options = vl_options or {}
        self._jinja_env = None
        self._jinja_template = None
        self._load_template(template_path)

    def _clean_ai_output(self, text):
        if not text:
            return ""

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        clean_json_text = re.sub(r"```json\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
        clean_json_text = re.sub(r"```\s*(.*?)\s*```", r"\1", clean_json_text, flags=re.DOTALL)

        try:
            match = re.search(r"\{.*\}", clean_json_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                for key in [
                    "response",
                    "interpretation",
                    "summary",
                    "translated_title",
                    "translation",
                    "title",
                    "abstract",
                    "content",
                ]:
                    if key in data and isinstance(data[key], str) and len(data[key]) > 2:
                        text = data[key]
                        break
                else:
                    for val in data.values():
                        if isinstance(val, str) and len(val) > 20:
                            text = val
                            break
        except Exception:
            pass

        redundant_patterns = [
            r"^Success[:：]?\s*",
            r"^OK[:：]?\s*",
            r"^生成成功[:：]?\s*",
            r"^翻译成功[:：]?\s*",
            r"^Thought[:：]?\s*.*?\n",
            r"^Invalid request format\.\s*",
            r'^\s*\{.*?"(title|translation|summary|response)"\s*:\s*',
            r"\}\s*$",
        ]
        for p in redundant_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        prefixes_to_remove = [
            r"^你是一个.*?\n",
            r"^直接返回.*?\n",
            r"^中文翻译[:：]\s*",
            r"^摘要翻译[:：]\s*",
            r"^标题翻译[:：]\s*",
            r"^Abstract[:：]\s*",
            r"^Title[:：]\s*",
            r"^翻译[:：]\s*",
        ]
        for p in prefixes_to_remove:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"^\s*[-*]\s+(.*)", r"• \1", text, flags=re.MULTILINE)

        text = text.strip()
        while text and (text[0] in "\"'{[: \n" or text[-1] in "\"'}]: \n"):
            text = (
                text.strip()
                .strip('"')
                .strip("'")
                .strip("}")
                .strip("{")
                .strip(":")
                .strip("]")
                .strip("[")
                .strip()
            )

        text = re.sub(r"^[a-zA-Z0-9_.]+\s*[:：]\s*", "", text)

        text = text.replace("\n", "<br/>")
        text = re.sub(r"(<br/>\s*){2,}", "<br/><br/>", text)
        text = re.sub(r"^(<br/>\s*)+|(<br/>\s*)+$", "", text)

        return text

    def _clean_ai_output(self, text):
        if not text:
            return ""

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        clean_json_text = re.sub(r"```json\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
        clean_json_text = re.sub(r"```\s*(.*?)\s*```", r"\1", clean_json_text, flags=re.DOTALL)

        try:
            match = re.search(r"\{.*\}", clean_json_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                for key in [
                    "response",
                    "interpretation",
                    "summary",
                    "translated_title",
                    "translation",
                    "title",
                    "abstract",
                    "content",
                ]:
                    if key in data and isinstance(data[key], str) and len(data[key]) > 2:
                        text = data[key]
                        break
                else:
                    for val in data.values():
                        if isinstance(val, str) and len(val) > 20:
                            text = val
                            break
        except Exception:
            pass

        redundant_patterns = [
            r"^Success[:：]?\s*",
            r"^OK[:：]?\s*",
            r"^生成成功[:：]?\s*",
            r"^翻译成功[:：]?\s*",
            r"^Thought[:：]?\s*.*?\n",
            r"^Invalid request format\.\s*",
            r'^\s*\{.*?"(title|translation|summary|response)"\s*:\s*',
            r"\}\s*$",
        ]
        for p in redundant_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        prefixes_to_remove = [
            r"^你是一个.*?\n",
            r"^直接返回.*?\n",
            r"^中文翻译[:：]\s*",
            r"^摘要翻译[:：]\s*",
            r"^标题翻译[:：]\s*",
            r"^Abstract[:：]\s*",
            r"^Title[:：]\s*",
            r"^翻译[:：]\s*",
        ]
        for p in prefixes_to_remove:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"^\s*[-*]\s+(.*)", r"• \1", text, flags=re.MULTILINE)

        text = text.strip()
        while text and (text[0] in "\"'{[: \n" or text[-1] in "\"'}]: \n"):
            text = (
                text.strip()
                .strip('"')
                .strip("'")
                .strip("}")
                .strip("{")
                .strip(":")
                .strip("]")
                .strip("[")
                .strip()
            )

        text = re.sub(r"^[a-zA-Z0-9_.]+\s*[:：]\s*", "", text)

        text = text.replace("\n", "<br/>")
        text = re.sub(r"(<br/>\s*){2,}", "<br/><br/>", text)
        text = re.sub(r"^(<br/>\s*)+|(<br/>\s*)+$", "", text)

        return text

    def select_best_image(self, image_paths):
        """Use VL model to select the best image from candidates."""
        if not image_paths:
            return None
        if not self.vl_model:
            logger.warning("VL model not configured, using first image.")
            return image_paths[0]

        try:
            b64_images = []
            # MAX_SIZE = (1024, 1024) # 移除图片压缩，使用原始图片以获得更好效果
            
            for p in image_paths:
                try:
                    with open(p, "rb") as f:
                        b64_str = base64.b64encode(f.read()).decode("utf-8")
                        b64_images.append(b64_str)
                except Exception as e:
                    logger.warning(f"Failed to read image {p}: {e}")

            if not b64_images:
                logger.warning("No valid images for VL model.")
                return image_paths[0]

            # Use prompt from config or default
            prompt = getattr(self.prompts, "image_selection", "Select the best image index (0, 1, 2...). Return only the number.")
            
            logger.info(f"Using VL model {self.vl_model} to select from {len(b64_images)} images...")
            
            # 增加重试机制，如果失败尝试减少图片数量或进一步压缩
            try:
                # 针对 CoT 思考模型，移除强制截断，给予足够的上下文
                # 完全依赖外部注入的配置 (vl_options)
                vl_opts = self.vl_options
                
                result = self.client.generate_text(
                    prompt,
                    model=self.vl_model,
                    images=b64_images,
                    options=vl_opts
                )
            except Exception as e:
                logger.error(f"VL model call failed: {e}. Trying fallback with fewer images...")
                # 降级策略：只取前 3 张
                vl_opts = self.vl_options
                if len(b64_images) > 3:
                    result = self.client.generate_text(
                        prompt,
                        model=self.vl_model,
                        images=b64_images[:3],
                        options=vl_opts
                    )
                else:
                    raise

            # Extract the first number found
            match = re.search(r"\d+", result)
            if match:
                idx = int(match.group())
                if 0 <= idx < len(image_paths):
                    logger.info(f"VL model selected image index: {idx}")
                    return image_paths[idx]
            
            logger.warning(f"VL model returned invalid selection: {result}")
        except Exception as e:
            logger.error(f"Image selection failed: {e}")
        
        # 终极兜底策略：选择文件大小最大的图片（通常清晰度最高）
        logger.info("Using fallback strategy: selecting image with largest file size.")
        try:
            best_img = max(image_paths, key=lambda p: os.path.getsize(p))
            return best_img
        except Exception:
            return image_paths[0]
        if not text:
            return ""

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        clean_json_text = re.sub(r"```json\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL)
        clean_json_text = re.sub(r"```\s*(.*?)\s*```", r"\1", clean_json_text, flags=re.DOTALL)

        try:
            match = re.search(r"\{.*\}", clean_json_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                for key in [
                    "response",
                    "interpretation",
                    "summary",
                    "translated_title",
                    "translation",
                    "title",
                    "abstract",
                    "content",
                ]:
                    if key in data and isinstance(data[key], str) and len(data[key]) > 2:
                        text = data[key]
                        break
                else:
                    for val in data.values():
                        if isinstance(val, str) and len(val) > 20:
                            text = val
                            break
        except Exception:
            pass

        redundant_patterns = [
            r"^Success[:：]?\s*",
            r"^OK[:：]?\s*",
            r"^生成成功[:：]?\s*",
            r"^翻译成功[:：]?\s*",
            r"^Thought[:：]?\s*.*?\n",
            r"^Invalid request format\.\s*",
            r'^\s*\{.*?"(title|translation|summary|response)"\s*:\s*',
            r"\}\s*$",
        ]
        for p in redundant_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        prefixes_to_remove = [
            r"^你是一个.*?\n",
            r"^直接返回.*?\n",
            r"^中文翻译[:：]\s*",
            r"^摘要翻译[:：]\s*",
            r"^标题翻译[:：]\s*",
            r"^Abstract[:：]\s*",
            r"^Title[:：]\s*",
            r"^翻译[:：]\s*",
        ]
        for p in prefixes_to_remove:
            text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)

        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"^\s*[-*]\s+(.*)", r"• \1", text, flags=re.MULTILINE)

        text = text.strip()
        while text and (text[0] in "\"'{[: \n" or text[-1] in "\"'}]: \n"):
            text = (
                text.strip()
                .strip('"')
                .strip("'")
                .strip("}")
                .strip("{")
                .strip(":")
                .strip("]")
                .strip("[")
                .strip()
            )

        text = re.sub(r"^[a-zA-Z0-9_.]+\s*[:：]\s*", "", text)

        text = text.replace("\n", "<br/>")
        text = re.sub(r"(<br/>\s*){2,}", "<br/><br/>", text)
        text = re.sub(r"^(<br/>\s*)+|(<br/>\s*)+$", "", text)

        return text

    def _render_latex(self, text):
        if not text:
            return ""
        converter = LatexNodes2Text()

        def repl(match):
            content = match.group(1)
            try:
                return converter.latex_to_text(content)
            except Exception:
                return content

        text = re.sub(r"\$\$(.*?)\$\$", repl, text, flags=re.DOTALL)
        text = re.sub(r"\$(.*?)\$", repl, text, flags=re.DOTALL)
        text = re.sub(r"\\\[(.*?)\\\]", repl, text, flags=re.DOTALL)
        text = re.sub(r"\\\((.*?)\\\)", repl, text, flags=re.DOTALL)
        return text

    def _load_template(self, template_path):
        if template_path and os.path.exists(template_path):
            template_dir = os.path.dirname(template_path) or "."
            template_name = os.path.basename(template_path)
            self._jinja_env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
            self._jinja_template = self._jinja_env.get_template(template_name)
            logger.info(f"成功加载 HTML 模板: {template_path}")
            return template_path

        self._jinja_env = Environment(autoescape=False)
        self._jinja_template = self._jinja_env.from_string("<div></div>")
        return template_path

    def _authors_display(self, authors_raw: str) -> str:
        authors_raw = authors_raw or ""
        author_list = [a.strip() for a in authors_raw.split(",") if a.strip()]
        if not author_list:
            return ""
        return ", ".join(author_list[:3]) + (" et al." if len(author_list) > 3 else "")

    def paper_to_template_data(self, paper_data: dict) -> dict:
        authors_display = self._authors_display(paper_data.get("authors", ""))
        doi_url = paper_data.get("doi") or paper_data.get("arxiv_url") or ""

        interpretation = paper_data.get("interpretation")
        if isinstance(interpretation, str):
            interpretation = interpretation.strip()
            if not interpretation or "总结生成失败" in interpretation:
                interpretation = None
        else:
            interpretation = None

        fig1_url = paper_data.get("fig1_url")
        if not fig1_url or str(fig1_url).strip() in {"", "None", "null"}:
            fig1_url = None

        return {
            "arxiv_url": paper_data.get("arxiv_url"),
            "authors_display": authors_display,
            "publish_time": paper_data.get("publish_time", ""),
            "doi_url": doi_url,
            "chinese_title": paper_data.get("chinese_title", ""),
            "chinese_abstract": paper_data.get("chinese_abstract", ""),
            "title": self._render_latex(str(paper_data.get("title", ""))),
            "abstract": self._render_latex(str(paper_data.get("abstract", ""))),
            "interpretation": self._render_latex(interpretation) if interpretation else None,
            "fig1_url": fig1_url,
        }

    def get_chinese_title(self, title):
        if not title or len(title.strip()) < 2:
            return title
        prompt = f'{self.prompts.chinese_title}\n\nTitle: {title}\n\n请直接返回 JSON 格式：{{"title": "..."}}'
        try:
            result = self.client.generate_text(prompt, options=self.ollama_options)
            return self._render_latex(self._clean_ai_output(result))
        except Exception:
            return title

    def get_chinese_abstract(self, abstract):
        if not abstract or len(abstract.strip()) < 10:
            return abstract
        prompt = f'{self.prompts.chinese_abstract}\n\nAbstract: {abstract}\n\n请直接返回 JSON 格式：{{"translation": "..."}}'
        try:
            result = self.client.generate_text(prompt, options=self.ollama_options)
            return self._render_latex(self._clean_ai_output(result))
        except Exception:
            return abstract

    def get_pdf_interpretation(self, pdf_text):
        if not pdf_text or len(pdf_text.strip()) < 100:
            return "PDF 内容过短，无法生成深度总结。", False

        prompt = f"""{self.prompts.paper_interpretation}

{self.prompts.paper_interpretation_format}

Content:
{pdf_text[:20000]}"""

        try:
            result_raw = self.client.generate_text(prompt, options=self.ollama_options)

            is_relevant = True
            interpretation = ""

            try:
                json_match = re.search(r"\{.*\}", result_raw, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    is_relevant = bool(data.get("is_relevant", True))
                    interpretation = data.get("interpretation", "")
            except Exception:
                pass

            if not interpretation:
                interpretation = self._clean_ai_output(result_raw)

            return self._render_latex(interpretation), is_relevant
        except Exception as e:
            logger.error(f"生成 PDF 总结或二次判定失败: {e}")
            return "深度总结生成失败。", True

    def render_full_article(self, related_papers: list, popular_papers: list) -> str:
        related_ctx = [self.paper_to_template_data(p) for p in (related_papers or [])]
        popular_ctx = [self.paper_to_template_data(p) for p in (popular_papers or [])]
        return self._jinja_template.render(related_papers=related_ctx, popular_papers=popular_ctx)
