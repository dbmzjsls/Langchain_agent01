from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from src.config.settings import settings
from src.tools.retry_decorator import tool_retry
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TavilySearchInput(BaseModel):
    """Tavily 搜索输入模型"""
    query: str = Field(description="要搜索的问题或关键词")

class TavilyTool(BaseTool):
    """Tavily 搜索工具"""
    name: str = "tavily_search"
    description: str = """
    用于在互联网上搜索信息的工具。
    输入：搜索查询（问题或关键词）
    输出：搜索结果（包含标题、内容、URL）
    适用场景：需要获取最新信息、事实查询、新闻搜索等
    """
    args_schema: Type[BaseModel] = TavilySearchInput

    def _fallback(self, query: str) -> str:
        """降级： Tavily 无法使用时，返回友好提示"""
        logger.warning("Tavily 搜索降级: %s", query[:80])
        return (
            f"网络搜索服务暂时不可用。以下是缓存/本地知识的相关信息：\n"
            f"您搜索的是: {query}\n"
            f"提示：请稍后再试，或尝试更精确的关键词。"
        )

    @tool_retry(attempts=2, min_wait=2, max_wait=8, fallback=None)
    def _run(self, query: str) -> str:
        """执行Tavily搜索"""
        try:
            api_key = settings.api.tavily_api_key.get_secret_value()
            if not api_key:
                logger.error("未配置 Tavily API Key")
                return "错误：未配置 Tavily API Key"

            # 创建 Tavily 客户端
            logger.info("Tavily 搜索: %s", query[:80])
            client = TavilyClient(api_key=api_key)
            # 执行搜索
            response = client.search(
                query=query,
                max_results=3,
                search_depth="basic"
            )
            # 提取结果
            results = [] # 用于存放结果
            # 没结果就返回空列表，enumerate索引从1开始
            for idx, result in enumerate(response.get("results",[]),1):
                results.append({
                    "序号": idx,
                    "标题": result.get("title","无标题"),
                    "内容": result.get("content","无内容")[:200] + "...",
                    "url": result.get("url", "")
                })

            if not results:
                logger.info("Tavily 搜索无结果: %s", query[:80])
                return "未搜索到结果"
            logger.info("Tavily 搜索成功，返回 %d 条结果", len(results))
            return str(results)
        except Exception as e:
            logger.error("Tavily 搜索失败: %s", str(e))
            return f"搜索错误:{str(e)}"