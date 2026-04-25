from typing import Type
from datetime import datetime, timezone, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from src.config.settings import settings
from src.utils.logger import get_logger
import requests
from urllib.parse import quote

logger = get_logger(__name__)

class WeatherQueryInput(BaseModel):
    city: str = Field(description='城市英文名称，例如 Beijing, Shanghai, Tokyo。不要使用中文，如果用户提供的是中文城市名，请先翻译为英文。')

class WeatherTool(BaseTool):
    name: str = "weather_query"
    description: str = "查询指定城市的实时天气信息。传入英文城市名查询。"
    args_schema: Type[BaseModel] = WeatherQueryInput

    def _fallback(self, city: str) -> str:
        """降级函数：当主 API 全部失败时， 尝试用 wttr.in 作为备选"""
        logger.warning("天气查询降级 (wttr.in): %s", city)
        try:
            resp = requests.get(
                f"https://wttr.in/{quote(city, safe='')}",
                params={"format": "%C+%t"},
                timeout=5,
            )
            if resp.status_code == 200:
                logger.info("天气查询降级成功: %s", city)
                return f"{city}天气（备选源）：{resp.text}"
        except Exception as e:
            logger.error("天气查询降级也失败: %s", str(e))
        return f"{city}天气查询服务暂时不可用"

    def _run(self, city: str) -> str:
        try:
            logger.info("天气查询: %s", city)
            api_key = settings.api.weather_api_key.get_secret_value()
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city,
                    "appid": api_key,
                    "units": "metric",
                    "lang": "zh_cn",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            # 从 dt 字段解析日期时间（北京时间 UTC+8）
            dt = datetime.fromtimestamp(data['dt'], tz=timezone.utc) + timedelta(hours=8)
            date_str = dt.strftime('%Y-%m-%d %H:%M')
            result = f"{city}天气({date_str}): {data['weather'][0]['description']}, 温度: {data['main']['temp']}°C"
            logger.info("天气查询成功: %s", result)
            return result
        except Exception as e:
            logger.error("天气查询失败: %s", str(e))
            return f"天气查询失败：{str(e)}"
