import requests
import logging

logger = logging.getLogger("DailyPaper")

class BarkNotifier:
    """
    Bark 消息通知工具类
    """
    def __init__(self, api_key):
        self.api_key = api_key
        
    def send(self, title, content, group="DailyPaper"):
        """
        发送 Bark 通知
        """
        if not self.api_key:
            return False
            
        url = f"https://api.day.app/{self.api_key}/"
        
        data = {
            "title": title,
            "body": content,
            "group": group,
            "icon": "https://cdn-icons-png.flaticon.com/512/2583/2583259.png"
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logger.info(f"Bark 通知发送成功: {title}")
                return True
            else:
                logger.error(f"Bark 通知发送失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Bark 通知发送异常: {e}")
            return False
