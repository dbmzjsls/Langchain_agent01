import logging

from mcp.server import FastMCP
from sqlalchemy import text

from src.tools.database_tool import engine
from datetime import datetime, timezone, timedelta
from src.config.settings import settings
import requests

logger = logging.getLogger(__name__)

# 创建实例
mcp = FastMCP("Agent MCP Server", json_response=True,host="127.0.0.1",port=8765)

# 动态暴露已有工具（复用原tool中的工具）
@mcp.tool()
def weather_query(city: str) ->str:
    """查询指定城市实时的天气信息"""
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

@mcp.tool()
def database_query(query:str) ->str:
    """执行 PostgreSQL 只读查询（仅 SELECT）。"""
    if not query.strip().upper().startswith("SELECT"):
        logger.warning("非法的数据库查询 (非 SELECT): %s", query[:80])
        return "错误：出于安全考虑，目前仅支持 SELECT 查询。"  # 格式错误，返回给AI

    try:
        logger.info("执行数据库查询: %s", query[:100])
        with engine.connect() as conn:
            result = conn.execute(text(query))  # 从结果中获取所有行并进行遍历，将所有行数据转化为字典对象，以字符串格式作为返回值
            rows = [row._asdict() for row in result.fetchall()]
            logger.info("数据库查询成功，返回 %d 行", len(rows))
            return str(rows)
    except Exception as e:
        logger.error("数据库查询失败: %s", str(e))
        return f"数据库错误{str(e)}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")