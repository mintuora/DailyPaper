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

    def generate_text(self, prompt, model=None, max_retries=3, options=None):
        target_model = model or self.model
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": options or {},
        }

        timeout = 600

        with self._gpu_lock:
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        wait_time = 5 * attempt
                        logger.info(f"正在进行第 {attempt} 次重试，等待 {wait_time}s...")
                        time.sleep(wait_time)

                    logger.info(f"正在调用 Ollama ({target_model})，请求排队中/处理中...")
                    response = requests.post(url, json=payload, timeout=timeout)
                    response.raise_for_status()

                    result = response.json()
                    content = result.get("response", "")

                    if not content:
                        raise Exception("Ollama 返回内容为空")

                    logger.info("Ollama 文本生成成功")
                    return content

                except Exception as e:
                    logger.error(
                        f"Ollama 调用异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    if attempt == max_retries:
                        raise
        return ""
