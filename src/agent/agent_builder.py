from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from src.agent.memory_manager import get_session_history
from src.config.settings import settings
from src.extractors.structured_extractor import StructuredExtractor
from src.tools.database_tool import DatabaseTool
from src.tools.mcp_client import MCPToolClient, mcp_tools_to_langchain
from src.tools.tavily_tool import TavilyTool
from src.tools.weather_tool import WeatherTool


class AgentBuilder:
    def __init__(self, mcp_enabled: bool = False):
        self.mcp_enable = mcp_enabled
        self.llm = ChatOpenAI(
            model=settings.llm,
            temperature=settings.temperature,
            api_key=settings.api.dashscope_api_key.get_secret_value(),
            base_url=settings.api.dashscope_base_url
        )
        # FC 硬编码工具（固定启动）
        self.fc_tools = [
            DatabaseTool(),
            WeatherTool(),
            TavilyTool(),
            StructuredExtractor(),
        ]

        # MCP 动态工具（运行时动态发现）
        self.mcp_tools = []
        if mcp_enabled:
            mcp_client = MCPToolClient()
            self.mcp_tools = mcp_tools_to_langchain(mcp_client)

    def build(self):
        # 定义 prompt,合并FC和MCP工具
        all_tools = self.fc_tools + self.mcp_tools

        prompt = ChatPromptTemplate.from_messages([
            ("system","你是一个基于 Langchain 构建的高级助手。"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        # 创建 Agent
        agent = create_tool_calling_agent(self.llm, all_tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=all_tools,
            max_iterations=settings.max_iterations
        )
        #使用 RunnableWithMessageHistory 包装
        agent_executor = RunnableWithMessageHistory(
            executor,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history"
        )
        return agent_executor