from typing import Dict

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from src.utils.logger import get_logger

logger = get_logger(__name__)

store: Dict[str, BaseChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    根据 session_id 返回对应的历史记录对象。
    Agent 会自动调用这个函数来读取和写入历史。
    """
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
        logger.debug("创建新会话历史: %s", session_id)
    logger.debug("获取会话历史: %s (共 %d 条消息)", session_id, len(store[session_id].messages))
    return store[session_id]