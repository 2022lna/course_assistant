import os
import datetime
import requests
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_tavily import TavilySearch
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class ToolManager:
    def __init__(self, env_path: str = "课程助手/lna.env"):
        """
        初始化工具管理器
        :param env_path: .env 文件路径
        """
        # 加载环境变量
        load_dotenv(env_path)

        # 初始化 Tavily 搜索工具
        self.search_tool = TavilySearch(max_results=5, topic="general")

    # ==================== 工具定义 ====================

    # ✅ 网页抓取工具 Schema 和函数
    class WebScrapingSchema(BaseModel):
        url: str = Field(description="要抓取的网页URL")
        extract_text: bool = Field(default=True, description="是否只提取文本内容")

    @tool(args_schema=WebScrapingSchema)
    def web_scraping(url: str, extract_text: bool = True) -> str:
        """
        抓取指定网页的内容。可以获取网页的文本内容或HTML源码。
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            if extract_text:
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text[:3000] + "\n\n[内容已截断...]" if len(text) > 3000 else text
            else:
                return response.text[:3000] + "\n\n[HTML内容已截断...]" if len(response.text) > 3000 else response.text
        except Exception as e:
            return f"网页抓取失败: {str(e)}"

    # ✅ 日期时间工具 Schema 和函数
    class DateTimeSchema(BaseModel):
        operation: str = Field(description="操作类型: now, format, calculate, timezone")
        date_string: str = Field(default="", description="日期字符串（用于格式化或计算）")
        format_string: str = Field(default="%Y-%m-%d %H:%M:%S", description="日期格式")
        days_offset: int = Field(default=0, description="天数偏移量（用于日期计算）")

    @tool(args_schema=DateTimeSchema)
    def datetime_operations(operation: str, date_string: str = "", format_string: str = "%Y-%m-%d %H:%M:%S", days_offset: int = 0) -> str:
        """
        执行日期时间相关操作，包括获取当前时间、格式化日期、日期计算等。
        """
        try:
            if operation == "now":
                return datetime.datetime.now().strftime(format_string)
            elif operation == "format":
                if date_string:
                    dt = datetime.datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                    return dt.strftime(format_string)
                else:
                    return "请提供要格式化的日期字符串"
            elif operation == "calculate":
                base_date = datetime.datetime.now()
                if date_string:
                    base_date = datetime.datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                new_date = base_date + datetime.timedelta(days=days_offset)
                return new_date.strftime(format_string)
            elif operation == "timezone":
                import time
                utc_offset = time.timezone // 3600
                dst_offset = time.altzone // 3600 if time.daylight else utc_offset
                return f"当前时区: {time.tzname[0]}/{time.tzname[1] if time.daylight else ''}, UTC偏移: {utc_offset if not time.daylight else dst_offset} 小时"
            else:
                return f"不支持的操作类型: {operation}"
        except Exception as e:
            return f"日期时间操作失败: {str(e)}"

    # ✅ 天气查询工具 Schema 和函数
    class WeatherQuerySchema(BaseModel):
        city: str = Field(..., description="要查询天气的城市名称，如 北京、上海、纽约")

    @tool(args_schema=WeatherQuerySchema)
    def get_realtime_weather(city: str) -> str:
        """
        查询指定城市的实时天气情况，使用 wttr.in 免费服务。
        - 支持中文城市名
        - 无需 API Key
        返回：天气状况、温度、风速、湿度等信息（纯文本格式）
        """
        url = f"https://wttr.in/{city}"
        params = {
            "format": 2,  # 简洁格式：城市: 天气, 温度
            "lang": "zh"  # 中文显示
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.text.strip()
            else:
                return f"天气查询失败：HTTP {response.status_code}"
        except Exception as e:
            return f"查询天气时出错: {str(e)}"

    # ✅ 获取所有工具列表
    def get_tools(self) -> List:
        """
        返回所有可用工具的列表，供 Agent 使用
        """
        return [
            self.search_tool,           # Tavily 搜索
            self.web_scraping,          # 网页抓取
            self.datetime_operations,   # 日期时间操作
            self.get_realtime_weather,  # 实时天气查询
            
        ]

    # ✅ 打印所有工具名称（调试用）
    def print_tools(self):
        """打印所有工具名称和描述"""
        tools = self.get_tools()
        for tool in tools:
            print(f"🔧 {tool.name}: {tool.description}")

if __name__ == "__main__":
    # ================== 创建 AgentExecutor ==================
    from langchain_openai import ChatOpenAI
    # from langchain import hub
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    load_dotenv("课程助手/lna.env")
    # 🔧 1. 初始化语言模型（以 GPT-3.5-turbo 为例）
    llm = ChatOpenAI(
        model="qwen-max",
        # temperature=0,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        streaming=True
    )

    tool_ = ToolManager()
    # 🔧 2. 准备工具列表
    # tools = [
    #     search_tool,      # Tavily 搜索
    #     web_scraping,      # 网页抓取
    #     get_realtime_weather, # 实时天气查询
    #     datetime_operations # 日期时间操作
    # ]


    # 🔧 3. 创建 prompt（使用 LangChain 官方推荐的 agent prompt）
    # 你可以自定义，也可以用 hub 上的标准模板
    # ✅ 创建提示词模板
    system_prompt = """
    你是一名经验丰富的智能助手，擅长帮助用户高效完成各种任务。你拥有以下强大的工具能力：

    ## 🔍 搜索和信息获取工具
    1. **Tavily搜索 (search_tool)**: 高质量的网络搜索，适合获取最新信息和新闻
    2. **网页抓取 (web_scraping)**: 抓取指定网页的内容，可获取文本或HTML源码
    3. **实时天气查询 (get_realtime_weather)**: 查询指定城市的实时天气情况，使用 wttr.in 免费服务
    4. **日期时间操作 (datetime_operations)**: 执行日期时间相关操作，包括获取当前时间、格式化日期、日期计算等。


    ## 🎯 工具使用指南

    **搜索信息时：**
    - 最新新闻、实时信息 → 使用 `search_tool`
    - 特定网页内容 → 使用 `web_scraping`
    **时间处理时：**
    - 获取当前时间、日期计算 → 使用 `datetime_operations`
    **天气查询时：**
    - 实时天气 → 使用 `get_realtime_weather`
    """

    from langchain.prompts import ChatPromptTemplate,MessagesPlaceholder
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        # MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # 🔧 4. 创建 agent
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tool_.get_tools(),
        prompt=prompt
    )

    # 🔧 5. 创建 AgentExecutor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tool_.get_tools(),
        verbose=True,           # 打印思考过程
        handle_parsing_errors=True  # 自动处理解析错误
    )

    # ================== 测试 Agent ==================
    print("🔍 正在测试 Agent，请输入你的问题（输入 'quit' 退出）：\n")
    while True:
        query = input("User: ").strip()
        if query.lower() in ["quit", "exit", "退出"]:
            print("👋 再见！")
            break
        if query:
            try:
                result = agent_executor.invoke({"input": query})
                print(f"AI: {result['output']}\n")
            except Exception as e:
                print(f"❌ 执行出错: {e}\n")