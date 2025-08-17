import os
import datetime
import requests
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_tavily import TavilySearch
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json
from urllib.parse import quote

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




    # ✅ 创建百度搜索工具
    class BaiduSearchSchema(BaseModel):
        query: str = Field(description="搜索查询关键词")
        num_results: int = Field(default=5, description="返回结果数量，默认5个")
    
    @tool(args_schema=BaiduSearchSchema)
    def baidu_search(query: str, num_results: int = 5) -> str:
        """
        使用百度搜索获取信息，对中文搜索友好。
        百度相比谷歌对爬虫更宽松，适合中文内容搜索。
        """
        
        # 构建百度搜索URL
        search_url = "https://www.baidu.com/s"
        params = {
            'wd': query,
            'pn': 0,  # 页码，百度是10个结果一页
            'rn': num_results if num_results <= 50 else 50,  # 百度最多返回50个结果
            'ie': 'utf-8'
        }
        
        # 百度搜索请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        try:
            # 先尝试不使用代理
            try:
                response = requests.get(search_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
            except requests.exceptions.RequestException:
                # 如果失败，尝试使用代理
                proxies = {
                    "http": "http://127.0.0.1:7890",
                    "https": "http://127.0.0.1:7890"
                }
                response = requests.get(search_url, params=params, headers=headers, timeout=15, proxies=proxies)
                response.raise_for_status()
            
            # 设置正确的编码
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否遇到验证码
            if "输入验证码" in response.text or "请输入验证码" in response.text:
                return "⚠️ 百度搜索遇到验证码验证，请稍后重试"
            
            results = []
            
            # 百度搜索结果的多种选择器
            # 选择器1: 标准搜索结果
            search_results = soup.find_all('div', {'class': 'result'})
            
            # 选择器2: 新版百度结果
            if not search_results:
                search_results = soup.find_all('div', {'class': 'c-container'})
            
            # 选择器3: 通用结果容器
            if not search_results:
                search_results = soup.find_all('div', {'tpl': True})
            
            # 选择器4: 最通用的选择器
            if not search_results:
                search_results = soup.find_all('div', recursive=True)
                search_results = [div for div in search_results 
                                if div.find('h3') and div.find('a') 
                                and len(div.get_text().strip()) > 50]
            
            for i, result in enumerate(search_results[:num_results]):
                try:
                    # 提取标题
                    title_elem = result.find('h3') or result.find('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text().strip()
                    if not title:
                        continue
                    
                    # 提取链接
                    link_elem = result.find('a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    link = link_elem.get('href')
                    
                    # 清理百度重定向链接
                    if link.startswith('http://www.baidu.com/link?url='):
                        # 百度的重定向链接，暂时保留原链接
                        pass
                    elif link.startswith('/'):
                        # 相对链接，跳过
                        continue
                    
                    # 提取描述文本
                    snippet = "无描述"
                    
                    # 百度描述的多种选择器
                    snippet_selectors = [
                        '.c-abstract',
                        '.c-span9',
                        '.c-span-last',
                        'span[style*="color:#999"]',
                        '.c-color-text',
                        'span.c-color-gray',
                        'font[size="-1"]'
                    ]
                    
                    for selector in snippet_selectors:
                        snippet_elem = result.select_one(selector)
                        if snippet_elem:
                            snippet = snippet_elem.get_text().strip()
                            # 清理百度特有的标记
                            snippet = snippet.replace('...', '').strip()
                            break
                    
                    # 如果仍然没有描述，尝试从整个结果中提取
                    if snippet == "无描述":
                        text_content = result.get_text().strip()
                        if len(text_content) > len(title) + 20:
                            snippet = text_content.replace(title, '', 1).strip()
                            # 取前200个字符
                            snippet = snippet[:200] + ('...' if len(snippet) > 200 else '')
                    
                    # 清理标题和描述中的多余空白
                    title = ' '.join(title.split())
                    snippet = ' '.join(snippet.split())
                    
                    if title and link:
                        results.append({
                            'title': title,
                            'link': link,
                            'snippet': snippet
                        })
                        
                except Exception as e:
                    continue  # 跳过有问题的结果
            
            if results:
                return json.dumps(results, ensure_ascii=False, indent=2)
            else:
                return "🔍 未找到搜索结果，可能的原因：\n1. 搜索词过于特殊\n2. 网络连接问题\n3. 百度页面结构变化\n\n建议尝试其他搜索工具。"
                
        except requests.exceptions.ProxyError:
            return "❌ 代理连接失败，请检查代理设置"
        except requests.exceptions.ConnectionError:
            return "❌ 网络连接失败，请检查网络连接"
        except requests.exceptions.Timeout:
            return "❌ 请求超时，请稍后重试"
        except Exception as e:
            return f"❌ 百度搜索失败: {str(e)}\n建议使用其他搜索工具"

    # ✅ 获取所有工具列表
    def get_tools(self) -> List:
        """
        返回所有可用工具的列表，供 Agent 使用
        """
        return [
            self.search_tool,           # Tavily 搜索
            self.baidu_search,          # 百度搜索
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
    1. **Tavily搜索 (search_tool)**: 🥇 专业搜索API，稳定可靠，适合获取最新信息和新闻
    2. **百度搜索 (baidu_search)**: 🌟 对中文搜索友好，无反爬虫问题，推荐用于中文内容搜索
    3. **网页抓取 (web_scraping)**: 📄 抓取指定网页的内容，可获取文本或HTML源码
    4. **实时天气查询 (get_realtime_weather)**: ☀️ 查询指定城市的实时天气情况
    5. **日期时间操作 (datetime_operations)**: 🕐 获取当前时间、格式化日期、日期计算等

    ## 🎯 工具使用策略

    **搜索信息时：**
    - 🥇 首选：`search_tool` (Tavily) - 专业、稳定、准确
    - 🌟 中文搜索：`baidu_search` - 中文内容友好，稳定可靠
    - 📄 特定页面：`web_scraping` - 获取具体网页内容

    **其他工具：**
    - ☀️ 天气查询：`get_realtime_weather`
    - 🕐 时间处理：`datetime_operations`

    **搜索顺序建议：** Tavily → 百度搜索
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