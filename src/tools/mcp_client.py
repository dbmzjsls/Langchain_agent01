import asyncio

from langchain_core.tools import BaseTool
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import Field, create_model, BaseModel


class MCPToolClient:
    def __init__(self, server_url:str = "http://localhost:8765/mcp"):
        self.server_url = server_url
        self._tool_meta = [] # 数据缓存

    # 方法一：发现工具
    async def _discover_async(self) -> list[dict]:
        """异步连接 MCP Server, 调用list_tools(), 返回含有工具的列表"""
        async with streamable_http_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()# 无状态连接，每次会话都重新握手
                response = await session.list_tools() # 向服务器发送tools/list请求，异步等待
                return[
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema":t.inputSchema,
                    }
                    for t in response.tools # 只要返回的一大堆响应对象里面的工具列表
                ]

    def discover(self) -> list[dict]:
        """LangChain的工具调用是同步的，采用同步封装"""
        self._tool_meta = asyncio.run(self._discover_async())
        return self._tool_meta

    # 方法二：调用工具
    async def _call_async(self,tool_name:str,arguments:dict) -> str:
        """调用MCP后返回的结果"""
        async with streamable_http_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize() # 无状态连接，每次会话都重新握手
                result = await session.call_tool(tool_name, arguments=arguments)
                text_contents = []
                for content_item in result.content:
                    if content_item.type == "text":# 获取文本内容
                        text_contents.append(content_item.text)
                return "".join(text_contents) # 将内容合并为字符串返回

    def call_tool(self, tool_name:str, arguments:dict) -> str:
        """同步封装（同上）"""
        return asyncio.run(self._call_async(tool_name, arguments))

def mcp_tools_to_langchain(client:MCPToolClient) -> list[dict]:
    """将 MCP Server上的所有工具转化为LangChain BaseTool列表，方便Agent读取"""
    tool_meta = client.discover() # 先发现工具
    result = [] # 缓存内容
    for meta in tool_meta:
        tool = _create_one_tool(meta, client)
        result.append(tool)
    return result

# 自动化创建 MCP 服务工厂
def _create_one_tool(meta:dict, client:MCPToolClient) -> BaseTool:
    """
    说人话：MCP协议是基于 JSON-RPC定义的工具格式，必须要转化成langchain可以调用的BaseTool实例
    """
    # 动态创建 Pydantic Input Schema.作为说明书
    input_schema = meta.get("input_schema",{}) # 从input_schema中提取字段，通常为JSON结构
    properties = input_schema.get("properties",{})

    fields = {}
    for field_name, field_info in properties.items():
        # 字段类型，简单起见当做str
        fields[field_name] = (str, Field(description=field_info.get("description","")))

    # 动态建模：利用Pydantic 的 create_model功能，创建一下LangChain的Agent知道如何填写的参数
    dynamical = create_model(f"{meta['name']}_input", **fields) if fields else BaseModel

    # 创建 LangChain BaseTool子类
    class MCPBridgeTool(BaseTool):
        # 从_run()中调用 MCP Client 的 call_tool()
        name:str = meta["name"]
        description:str = f"[MCP]{meta['description']}"
        args_schema:type[BaseModel] = dynamical

        def _run(self,**kwargs) -> str:
            return client.call_tool(meta['name'],kwargs) # 去请求真正的MCP服务器

    return MCPBridgeTool()
