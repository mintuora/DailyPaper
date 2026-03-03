import requests
import logging
import time
import threading

logger = logging.getLogger("DailyPaper")


class OllamaAPI:
    _gpu_lock = threading.Lock()

    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        logger.info(f"OllamaAPI initialized with base_url: {self.base_url}, model: {self.model}")

    def generate_text(self, prompt, model=None, max_retries=3, options=None, images=None):
        target_model = model or self.model
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": options or {},
        }
        if images:
            payload["images"] = images

        timeout = 600

        with self._gpu_lock:
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        wait_time = 5 * attempt
                        logger.info(f"正在进行第 {attempt} 次重试，等待 {wait_time}s...")
                        time.sleep(wait_time)

                    logger.info(f"正在调用 Ollama ({target_model})，请求排队中/处理中...")
                    start_time = time.time()
                    response = requests.post(url, json=payload, timeout=timeout)
                    elapsed = time.time() - start_time
                    
                    try:
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        logger.error(f"Ollama HTTP 错误: {e}, Response: {response.text[:200]}")
                        raise

                    result = response.json()
                    content = result.get("response", "")
                    
                    # 尝试从 thinking 字段中提取（针对 CoT 模型）
                    if not content and "thinking" in result:
                        thinking = result["thinking"]
                        if thinking:
                            logger.warning(f"Ollama response is empty, trying to extract from thinking: {thinking[:100]}...")
                            # 简单的启发式：如果是数字选择题，尝试找最后的数字
                            import re
                            match = re.findall(r"\b\d\b", thinking)
                            if match:
                                content = match[-1]
                                logger.info(f"Extracted '{content}' from thinking.")
                            else:
                                # 如果无法提取，则认为失败，抛出异常以便触发重试或兜底
                                logger.warning("Could not extract valid content from thinking.")

                    if not content:
                        logger.error(f"Ollama 返回空内容. Payload size: {len(str(payload))}, Elapsed: {elapsed:.2f}s, Result: {result}")
                        raise Exception("Ollama 返回内容为空")

                    logger.info(f"Ollama 文本生成成功 (耗时 {elapsed:.2f}s)")
                    return content

                except Exception as e:
                    logger.error(
                        f"Ollama 调用异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    if attempt == max_retries:
                        raise
        return ""
