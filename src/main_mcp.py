"""MCP模式：混合FC+MCP工具调用"""
import subprocess
import sys
import time
import uuid

from src.agent.agent_builder import AgentBuilder
from src.utils.logger import get_logger

logger = get_logger(__name__)

def start_mcp_server():
    """后台启动 MCP Server 进程"""
    proc = subprocess.Popen(
        [sys.executable, "src/tools/mcp_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2) # 等待服务器启动
    logger.info("MCP Server 已启动（PID=%d）",proc.pid)
    return proc

def main():
    mcp_proc = start_mcp_server()
    try:
        # 构建支持 MCP 的Agent
        builder = AgentBuilder(mcp_enabled=True)
        agent_chain = builder.build()
        session_id = str(uuid.uuid4())
        logger.info("FC+MCP混合模型已就绪")

        # 循环交互
        while True:
            user_input = input("\n用户(按'q'退出)：")
            if user_input.lower() in ["q", "exit", "quit"]:
                break
            response = agent_chain.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}},
        )
            print(f"小助手: {response['output']}")
    finally:
        mcp_proc.terminate()
        logger.info("MCP Server 已关闭")
if __name__ == "__main__":
    main()