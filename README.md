# LangChain 智能 Agent 对话系统

基于 **LangChain** 框架构建的智能对话 Agent，以大语言模型为推理核心，集成多种实用工具（数据库查询、互联网搜索、天气查询），通过命令行交互界面为用户提供智能化服务。

---

## 架构概览

```
用户输入 (CLI)
    │
    ▼
┌─────────────────────────────────────┐
│         RunnableWithMessageHistory   │  ← 多轮对话记忆
│  ┌───────────────┐                  │
│  │  AgentExecutor │  (max 4 轮迭代) │  ← 工具调用循环
│  │  ┌───────────┐ │                │
│  │  │Tool Calling│ │                │  ← LLM 推理 + 工具选择
│  │  │   Agent    │ │                │
│  │  └─────┬─────┘ │                │
│  └────────┼───────┘                │
└───────────┼────────────────────────┘
            │
    ┌───────┼───────┬──────────────┐
    ▼       ▼       ▼              ▼
┌──────┐ ┌──────┐ ┌──────┐  ┌──────────┐
│数据库 │ │天气  │ │搜索  │  │结构化提取 │    ← FC 硬编码工具
│查询  │ │查询  │ │工具  │  │(独立能力) │
└──────┘ └──────┘ └──────┘  └──────────┘
    │       │       │              │
    └───────┴───────┴──────────────┘
                    │
          ┌─────────▼─────────┐
          │   MCP Server      │  ← FastMCP 动态暴露工具
          │ (streamable_http) │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │   MCP Client      │  ← 自动发现 + 动态 Bridge
          │ (BaseTool 适配)   │
          └───────────────────┘
```

**FC 模式（默认）：** LLM 直接调用硬编码工具
**MCP 混合模式：** LLM → AgentExecutor → MCP Client (工具发现+适配) → MCP Server (工具暴露) → 实际工具函数

---

## 核心功能

| 模块 | 能力 | 实现方式 |
|------|------|----------|
| **数据库查询** | 对 PostgreSQL 执行只读 SELECT 查询 | SQLAlchemy 连接池 + 安全限制（禁止非 SELECT 操作） |
| **互联网搜索** | 搜索互联网获取最新信息 | Tavily Search API（专为 LLM 优化的搜索引擎） |
| **天气查询** | 查询全球城市实时天气 | OpenWeatherMap API，失败自动降级至 wttr.in |
| **对话记忆** | 按 session 管理多轮对话上下文 | 内存存储的 InMemoryChatMessageHistory |
| **结构化提取** | 从文本中按 Schema 提取结构化信息 | LLM `with_structured_output()` + Pydantic Schema |
| **容错重试** | 网络异常自动重试 + 降级方案 | tenacity 指数退避重试 + 自定义 fallback 机制 |
| **MCP 混合模式** | FC 工具动态暴露为 MCP Server，Agent 通过 MCP Client 自动发现并调用 | FastMCP + streamable_http + 动态 BaseTool 适配 |

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **框架** | LangChain 1.0+ (langchain-core, langchain-openai, langchain-classic, langchain-community) |
| **LLM 提供商** | 阿里云百炼 (DashScope) — 兼容 OpenAI API，可切换 DeepSeek / 智谱 GLM |
| **数据库** | PostgreSQL + SQLAlchemy 2.0 (QueuePool 连接池) |
| **配置管理** | Pydantic Settings (自动加载 .env) |
| **搜索引擎** | Tavily Search API |
| **天气 API** | OpenWeatherMap + wttr.in (降级备份) |
| **重试机制** | tenacity (指数退避) |
| **日志** | Python logging (UTF-8 中文兼容) |
| **性能分析** | py-spy + snakeviz |
| **包管理** | uv |

---

## 项目结构

```
Langchain_agent01/
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── pyproject.toml              # 项目元数据与依赖
├── uv.lock                     # 依赖版本锁文件
├── README.md                   # 本文件
└── src/
    ├── main.py                 # 程序入口 — FC 模式（CLI 交互循环）
    ├── main_mcp.py             # 程序入口 — MCP 混合模式
    ├── agent/
    │   ├── agent_builder.py    # Agent 组装器 (LLM + FC工具 + MCP工具 + Prompt + 记忆)
    │   └── memory_manager.py   # 对话历史管理器
    ├── config/
    │   └── settings.py         # 全局配置 (Pydantic Settings, 三层嵌套)
    ├── tools/
    │   ├── database_tool.py    # PostgreSQL 只读查询工具
    │   ├── tavily_tool.py      # Tavily 互联网搜索工具
    │   ├── weather_tool.py     # OpenWeatherMap 天气查询工具
    │   ├── retry_decorator.py  # 通用重试 + 降级装饰器
    │   ├── mcp_server.py       # FastMCP Server (动态暴露 FC 工具)
    │   └── mcp_client.py       # MCP Client (自动发现 + 动态 BaseTool 适配)
    ├── extractors/
    │   └── structured_extractor.py  # 结构化数据提取器
    └── utils/
        └── logger.py           # 日志工具
```

---

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 包管理器
- PostgreSQL 数据库（如需使用数据库查询工具）

### 1. 克隆并安装依赖

```bash
cd Langchain_agent01
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填入你的 API Key：

```env
# LLM 服务 (阿里云百炼)
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 默认模型 (可切换为 deepseek-chat / glm-4 等)
LLM_MODEL_NAME=glm-5
LLM_TEMPERATURE=0.2

# Tavily 搜索
TAVILY_API_KEY=your_tavily_api_key

# OpenWeatherMap (天气查询)
WEATHER_API_KEY=your_weather_api_key

# PostgreSQL (数据库查询 - 可选)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. 运行

**FC 模式（默认）：**
```bash
uv run python -m src.main
```

**MCP 混合模式：**
```bash
uv run python -m src.main_mcp
```

> MCP 混合模式会自动启动 MCP Server 后台进程，Agent 通过 MCP Client 动态发现工具。两种模式共用同一套 FC 工具，区别在于调用路径不同。

进入交互式命令行后，可以直接用自然语言提问，例如：

- "帮我查一下北京今天的天气"
- "查询数据库中所有用户表"
- "搜索一下 LangChain 最新版本发布了哪些新特性"
- 输入 `exit` 或 `quit` 退出

---

## 工具详解

### DatabaseTool — 数据库查询

- 使用 SQLAlchemy `QueuePool` 连接池（pool_size=5, max_overflow=10）
- **安全限制**：仅允许 `SELECT` 语句，拒绝 INSERT / UPDATE / DELETE / DROP 等写操作
- 支持重试（2 次，指数退避 1~3 秒），失败后返回降级提示

### WeatherTool — 天气查询

- 通过 OpenWeatherMap API 查询实时天气
- 返回：天气描述、温度（摄氏度）、数据采集时间（北京时间）
- **双重容错**：主 API 失败 → 自动降级到免费的 `wttr.in` 接口
- 输入要求英文城市名（Agent 自动翻译中文城市名）

### TavilyTool — 互联网搜索

- 通过 Tavily Search API 进行互联网搜索（专为 AI Agent 优化）
- 每次搜索返回最多 3 条结果（含标题、摘要 200 字、URL）
- 支持重试（2 次，指数退避 2~8 秒）

### MCP Server & Client — MCP 协议桥接

- 使用 **FastMCP** 将已有的 FC 工具（天气查询、数据库查询）动态暴露为 MCP Server
- 基于 `streamable_http` 传输协议，支持无状态连接
- **MCP Client** 通过 `list_tools()` 自动发现 Server 上的工具
- 自动化工厂 `_create_one_tool()`：读取 MCP 工具的 `inputSchema` → 动态创建 Pydantic model → 生成 LangChain `BaseTool` 子类
- 关键点：`args_schema` 字段必须正确设置为动态 Pydantic model，LangChain 才能将参数定义传递给 LLM

### retry_decorator — 通用容错机制

- `@tool_retry(max_retries=2, min_wait=1, max_wait=3)` 装饰器
- 仅对网络异常触发重试（`ConnectionError`, `TimeoutError`, `OSError`）
- 所有重试失败后自动调用 fallback 降级函数
- 基于 tenacity 库的指数退避策略

### 性能分析

项目包含性能分析工具：
```bash
# 使用 py-spy 进行性能分析
uv run py-spy record -o profile.svg -- python src/main.py

# 使用 snakeviz 可视化分析结果
uv run snakeviz profile.prof
```
---

## 设计亮点

| 特性 | 说明 |
|------|------|
| **完善的容错** | 每个工具都有重试 + 降级方案，天气工具甚至有两级降级 |
| **安全限制** | 数据库工具仅允许 SELECT，杜绝 SQL 注入和误操作风险 |
| **配置分离** | 敏感信息通过 `.env` 管理，`.env.example` 提供模板，不泄露密钥 |
| **模块化** | Agent 构建、工具、配置、日志职责分明，易于扩展新工具 |
| **多轮对话** | 基于 `RunnableWithMessageHistory` 实现 session 级别的对话记忆 |
| **多模型兼容** | 兼容阿里云百炼、DeepSeek、智谱 GLM 等国产模型，OpenAI 兼容 API 即可接入 |
| **LangSmith 集成** | 内置 LangSmith 追踪支持，方便调试 Agent 行为 |

---

## 扩展指南
### 添加新工具

1. 在 `src/tools/` 下创建新的工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 可选使用 `@tool_retry` 添加重试和降级逻辑
4. 在 `agent_builder.py` 的 `tools` 列表中注册新工具

### 切换模型

修改 `.env` 中的以下变量：

```env
DASHSCOPE_BASE_URL=https://api.deepseek.com/v1    # 切换为 DeepSeek
DASHSCOPE_API_KEY=your_deepseek_key
LLM_MODEL_NAME=deepseek-chat
```

### 持久化对话记忆

当前使用内存存储，进程重启后历史丢失。可替换为 Redis 或数据库存储：修改 `memory_manager.py`，使用 `RedisChatMessageHistory` 或其他持久化实现即可。

---

## 注意事项

- 本项目版本 `0.2.0`，处于早期开发阶段，适合概念验证和本地开发测试
- 对话历史存储在内存中，进程重启即清空
- 数据库工具默认连接本地 PostgreSQL，请确保数据库已启动
- `.env` 文件包含敏感信息，请勿提交到版本控制（已在 `.gitignore` 中排除）
