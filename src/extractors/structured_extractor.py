from typing import Type

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserSchema(BaseModel):
    name: str = Field(..., description="姓名")
    email: str = Field(..., description="邮箱")

class ExtractInput(BaseModel):
    """结构化提取输入的参数"""
    text: str = Field(..., description="要提取信息的文本内容")

class StructuredExtractor(BaseTool):
    """
    从文本中提取结构化信息（姓名、邮箱）
    """
    name:str = "structured_extractor"
    description: str = """
        从文本中提取结构化信息，如姓名和邮箱地址。
        输入：一段包含个人信息或联系方式的文本
        输出：结构化提取结果（姓名、邮箱）
        适用场景：从非结构化文本中提取联系人信息、用户资料等
        """
    args_schema: Type[BaseModel] = ExtractInput


    def _run(self, text: str) -> str:
        """执行结构化提取"""
        try:
            logger.info("结构化提取: %s", text[:100])
            llm = ChatOpenAI(
                model=settings.llm,
                base_url=settings.api.dashscope_base_url,
                api_key=settings.api.dashscope_api_key.get_secret_value()
            )
            parser = PydanticOutputParser(pydantic_object=UserSchema)
            prompt = ChatPromptTemplate.from_template(
                "从以下文本中提取姓名和邮箱，以JSON格式输出。"
                "{text}"
                "{format_instructions}"
            )
            chain = prompt | llm | parser
            result: UserSchema = chain.invoke({
                "text": text,
                "format_instructions": parser.get_format_instructions()
            })
            logger.info("提取结果: name=%s, email=%s", result.name, result.email)
            return f"姓名: {result.name}, 邮箱: {result.email}"
        except Exception as e:
            logger.error("结构化提取失败: %s", str(e))
            return f"提取失败: {str(e)}"