from pydantic import Field, computed_field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.utils.logger import get_logger

logger = get_logger(__name__)


# 数据库配置
class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='DB_', extra="ignore", populate_by_name=True)

    # 让字段可以自动映射到环境变量
    host:str = 'localhost'
    port:int = 5432
    name:str = Field(...) # 强制映射，避免大小写产生的匹配不一致，也可以让变量命名更随意
    user:str = ''
    password:str = ''

    # 动态生成连接字符串（打包）
    @computed_field # 数据模型序列化，成为一种可以存储或者输出的格式，可以自由流动
    @property # 动态计算这个字符串，让访问方法就像访问变量，不需要加括号
    def connection_string(self)-> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

# API配置
class APIConfig(BaseSettings):
    dashscope_api_key:SecretStr = Field(...,alias='DASHSCOPE_API_KEY')
    dashscope_base_url:str = Field(...,alias='DASHSCOPE_BASE_URL')
    weather_api_key:SecretStr = Field(...,alias='WEATHER_API_KEY')
    tavily_api_key:SecretStr = Field(...,alias='TAVILY_API_KEY')
    model_config = SettingsConfigDict(env_file='.env',extra="ignore")

# 全局配置
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra="ignore")

    # 嵌套子配置
    db:DatabaseConfig = Field(default_factory=DatabaseConfig)
    api:APIConfig = Field(default_factory=APIConfig)

    # 本地配置
    llm:str = "glm-5"
    temperature: float = 0.2
    max_iterations: int = 4 # 最大执行循环次数

# 实例化
settings = Settings()
logger.info("配置加载完成: llm=%s, db_host=%s", settings.llm, settings.db.host)