import os
import logging
import requests
import json
import time
import re
from PIL import Image

logger = logging.getLogger("DailyPaper")


class WeChatPublisher:
    def __init__(self, config):
        self.config = config
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.proxy_url = config.get("proxy_url", "")
        self.access_token = None
        self.access_token_expire_time = 0

        if self.proxy_url:
            self.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            logger.info(f"✅ 已配置微信API代理: {self.proxy_url}")
        else:
            self.proxies = None

        logger.info("WeChatPublisher initialized successfully")

    def _make_request(self, method, url, **kwargs):
        if self.proxies:
            kwargs["proxies"] = self.proxies
        if "timeout" not in kwargs:
            kwargs["timeout"] = 30

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = requests.post(url, **kwargs)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                response.raise_for_status()
                return response

            except (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    delay = retry_delay * (2**attempt)
                    time.sleep(delay)
                else:
                    logger.error("所有重试都失败了")
                    raise
            except Exception as e:
                logger.error(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                raise

    def get_access_token(self):
        if not self.app_id or not self.app_secret:
            logger.error("微信公众号AppID和AppSecret未配置")
            raise ValueError("微信公众号AppID和AppSecret未配置")

        current_time = time.time()
        if self.access_token and (current_time + 200) < self.access_token_expire_time:
            return self.access_token

        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        response = self._make_request("GET", url)
        data = response.json()

        if "access_token" in data and "expires_in" in data:
            self.access_token = data["access_token"]
            self.access_token_expire_time = current_time + data["expires_in"]
            logger.info("✅ 获取微信公众号访问令牌成功")
            return self.access_token

        if data.get("errcode") == 40164:
            logger.error(f"❌ IP白名单错误: {data.get('errmsg')}")
        raise Exception(f"获取访问令牌失败: {data}")

    def format_for_wechat(self, content, title, author="", cover_image="", summary=""):
        try:
            formatted = content.replace("\n\n", "</p><p>")
            formatted = formatted.replace("\n", "<br/>")
            formatted = f"<p>{formatted}</p>"

            max_summary_length = 100
            article_summary = summary
            if not article_summary:
                plain_text = re.sub(r"<[^>]+>", "", content).replace("\n", " ")
                article_summary = (
                    plain_text[:max_summary_length] + "..."
                    if len(plain_text) > max_summary_length
                    else plain_text
                )

            return {
                "title": title[:64],
                "author": (author or "DailyPaper")[:20],
                "cover_image": cover_image,
                "summary": article_summary[:max_summary_length],
                "content": formatted,
            }
        except Exception as e:
            logger.error(f"文章格式化过程中出错: {e}")
            raise

    def publish_article(self, article, draft=True):
        try:
            if not self.app_id or not self.app_secret:
                return {"errcode": -1, "errmsg": "微信配置不完整"}

            token = self.get_access_token()

            cover_media_id = None
            if article.get("cover_image"):
                cover_media_id = self._upload_image(article["cover_image"], is_cover=True)

            article_data = {
                "title": article["title"],
                "author": article["author"],
                "digest": article["summary"],
                "content": article["content"],
                "content_source_url": "",
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
            if cover_media_id:
                article_data["thumb_media_id"] = cover_media_id

            url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

            request_data = {"articles": [article_data]}
            json_data = json.dumps(request_data, ensure_ascii=False).encode("utf-8")
            headers = {"Content-Type": "application/json; charset=utf-8"}

            response = self._make_request("POST", url, data=json_data, headers=headers)
            result = response.json()

            if result.get("errcode", 0) != 0:
                logger.error(f"保存草稿失败: {result}")
                raise Exception(f"保存草稿失败: {result}")

            logger.info(f"✅ 保存草稿成功: {result.get('media_id')}")
            return result
        except Exception as e:
            logger.error(f"保存草稿过程中出错: {e}")
            raise

    def mass_send(self, media_id):
        token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token={token}"

        request_data = {
            "filter": {"is_to_all": True},
            "mpnews": {"media_id": media_id},
            "msgtype": "mpnews",
            "send_ignore_reprint": 0,
        }

        json_data = json.dumps(request_data, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}

        response = self._make_request("POST", url, data=json_data, headers=headers)
        result = response.json()

        if result.get("errcode", 0) != 0:
            logger.error(f"群发推送失败: {result}")
            return result

        logger.info(f"✅ 群发推送成功: {result.get('msg_id')}")
        return result

    def publish(self, media_id):
        token = self.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"

        request_data = {"media_id": media_id}

        json_data = json.dumps(request_data, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}

        response = self._make_request("POST", url, data=json_data, headers=headers)
        result = response.json()

        if result.get("errcode", 0) != 0:
            logger.error(f"普通发布失败: {result}")
            return result

        logger.info(f"✅ 普通发布成功: {result.get('publish_id')}")
        return result

    def upload_image(self, image_path, is_cover=False):
        return self._upload_image(image_path, is_cover=is_cover)

    def _upload_image(self, image_path, is_cover=True):
        token = self.get_access_token()
        if is_cover:
            url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
            temp_cover = self._resize_image(image_path)
            try:
                with open(temp_cover, "rb") as f:
                    data = {"description": json.dumps({"title": "封面图片"})}
                    files = {"media": f}
                    response = self._make_request("POST", url, data=data, files=files)
            finally:
                if os.path.exists(temp_cover):
                    os.remove(temp_cover)
        else:
            url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
            with open(image_path, "rb") as f:
                files = {"media": f}
                response = self._make_request("POST", url, files=files)

        result = response.json()
        if result.get("media_id"):
            return result["media_id"]
        if result.get("url"):
            return result["url"]
        raise Exception(f"图片上传失败: {result}")

    def _resize_image(self, image_path, target_width=900, target_height=383):
        try:
            if image_path.lower().endswith(".svg"):
                logger.warning(f"跳过 SVG 图片尺寸调整: {image_path}")
                return image_path

            with Image.open(image_path) as img:
                img.thumbnail((target_width * 2, target_height * 2), Image.LANCZOS)
                temp_filename = f"temp_wechat_cover_{int(time.time())}.jpg"
                img.convert("RGB").save(temp_filename, format="JPEG", quality=85)
                return temp_filename
        except Exception as e:
            logger.error(f"调整图片大小失败: {e}")
            return image_path
