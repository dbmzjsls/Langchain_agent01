import uuid

from src.agent.agent_builder import AgentBuilder
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    # 初始化 Builder，并且构建起链
    builder = AgentBuilder()
    agent_chain = builder.build() # 返回的是 RunnableWithMessageHistory 对象

    session_id = str(uuid.uuid4())
    logger.info("Agent 系统已就绪，session_id=%s", session_id)

    # 简单的同步循环
    while True:
        user_input = input("\n用户(按'q'退出)：")
        if user_input.lower() in ["q","exit", "quit"]:
            logger.info("用户退出对话")
            break

        # 调用 Agent
        # 通过 session_id 来读取历史，并自动保存新消息
        logger.info("用户输入: %s", user_input)
        response = agent_chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
        )

        # 返回结果
        # AgentExecutor返回的是dict对象
        output = response["output"]
        logger.info("Agent 返回: %s", output[:100])
        print(f"小助手:{output}")

if __name__ == "__main__":
    main()