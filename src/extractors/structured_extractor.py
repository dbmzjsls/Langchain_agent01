from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserSchema(BaseModel):
    name: str = Field(..., description="姓名")
    email: str = Field(..., description="邮箱")

class StructuredExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm,
            base_url=settings.api.dashscope_base_url,
            api_key=settings.api.dashscope_api_key.get_secret_value()
        )
        # 严格要求 LLM 按格式输出
        self.extractor = self.llm.with_structured_output(UserSchema)

    def extract(self, text: str) -> UserSchema:
        """执行文本，直接输出一个标准的 UserSchema 对象"""
        logger.info("结构化提取: %s", text[:100])
        result = self.extractor.invoke(text)
        logger.info("提取结果: name=%s, email=%s", result.name, result.email)
        return result