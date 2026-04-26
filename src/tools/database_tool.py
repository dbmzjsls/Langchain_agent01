from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text, QueuePool
from src.config.settings import settings
from src.tools.retry_decorator import tool_retry
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 使用模块基本连接池
engine = create_engine(
    settings.db.connection_string, # 数据库连接
    poolclass=QueuePool, # 连接池
    pool_size=5, # 提供 5 个闲置连接
    max_overflow=10, # 最大并发 +10
    pool_pre_ping=True,  # 使用前 ping 一下
)

# 给数据模型贴标签，并自动进行格式转化（双向）
class DatabaseQueryInput(BaseModel):
    query: str = Field(
        description="""用于执行 PostgreSQL 数据库只读查询的工具。输入必须是完整的 SELECT 语句。注意：INSERT/UPDATE/DELETE 等写操作会被拒绝。"""
    ) # 把query翻译成说明书

# 可以被外部系统 LangChain 调用
class DatabaseTool(BaseTool):
    name: str = "database_query"
    description: str = "查询 PostgresSQL 数据库。仅支持 SELECT 语句。"
    args_schema: Type[BaseModel] = DatabaseQueryInput # 把说明书加到工具上

    def _fallback(self, query: str) -> str:
        logger.warning("数据库查询降级: %s", query[:80])
        return "数据库连接异常， 请检查数据库服务是否正常运行"

    # 当工具被调用时，执行方法
    @tool_retry(attempts=2, min_wait=1, max_wait=3, fallback=None)
    def _run(self, query:str) -> str:
        if not query.strip().upper().startswith("SELECT"):
            logger.warning("非法的数据库查询 (非 SELECT): %s", query[:80])
            return "错误：出于安全考虑，目前仅支持 SELECT 查询。"  # 格式错误，返回给AI

        try:
            logger.info("执行数据库查询: %s", query[:100])
            with engine.connect() as conn:
                result = conn.execute(text(query))# 从结果中获取所有行并进行遍历，将所有行数据转化为字典对象，以字符串格式作为返回值
                rows = [row._asdict() for row in result.fetchall()]
                logger.info("数据库查询成功，返回 %d 行", len(rows))
                return str(rows)
        except Exception as e:
            logger.error("数据库查询失败: %s", str(e))
            return f"数据库错误{str(e)}"