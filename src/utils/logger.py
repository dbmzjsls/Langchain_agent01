import logging
import sys

# 日志格式：时间 - 模块 - 级别 - 消息
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Windows 终端兼容 UTF-8 中文输出
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_logger(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout) # 配置输出位置
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT) # 创建格式化器
        handler.setFormatter(formatter) # 定义的格式贴到处理器上
        logger.addHandler(handler) # 配置好的处理器添加到 logger 上
        logger.setLevel(level) # 配置 logger 级别

    return logger


logger = get_logger("langchain_agent")