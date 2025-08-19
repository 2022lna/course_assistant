from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
import os
from dotenv import load_dotenv
from intention import IntentionRecognizer
load_dotenv(r"课程助手/lna.env")
from my_tools import ToolManager
from rag_process import RAGProcess
import uuid
from history_management import HistoryManager
class AgentRouter:
    # 类变量，存储所有会话的历史
    store = {}
    intent_recognizer = IntentionRecognizer()#意图识别
    my_rag = RAGProcess()
    intention=''
    def __init__(self, session_id:str):
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.llm = ChatOpenAI(
            model="qwen-max",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            streaming=True
        )

        # 1. 定义各种 Prompt
        self.prompts = {
            "normal": ChatPromptTemplate.from_messages([
                ("system", """你是一个优秀的聊天助手，根据用户的提问和历史对话回答用户问题，
                 如果历史对话中的信息能够回答用户问题，你需要使用历史对话中的信息。
                 如果回答不了用户问题请一定要按照下面提示回答用户：
                 1.当用户的问题涉及实时信息或者需要联网搜索时，你需要提醒用户切换模式，如：请选择联网搜索模式，我将为您搜索相关信息。
                 2.当用户问题涉及到课程相关内容时，你需要提醒用户切换模式，如：请选择课程咨询模式，我将为您查询相关课程内容。
                 3.当用户提及上传的文件内容时，你需要提醒用户请先上传文件，如：请选择上传文件模式并上传文件，我才能为您查询文件内容。
                 三个模式名称不能改变，其他话术可以随机应变。
                 """),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
            ]),
            "search": ChatPromptTemplate.from_template("""
                你是一名经验丰富的智能助手，擅长帮助用户高效完成各种任务。你拥有以下强大的工具能力：
                {tools}  # ← 必须添加：工具列表（由 LangChain 自动注入）
                可用工具名称：{tool_names}  # ← 必须添加：工具名列表
                ## 🔍 工具使用指南
                **搜索信息时：**
                - 最新新闻、实时信息 → 使用 `search_tool`
                - 特定网页内容 → 使用 `web_scraping`
                **时间处理时：**
                - 获取当前时间、日期计算 → 使用 `datetime_operations`
                **天气查询时：**
                - 实时天气 → 使用 `get_realtime_weather`

                请使用 ReAct 格式进行思考和行动：
                Thought: 你应该思考是否需要使用工具
                Action: 工具名称（必须是 [{tool_names}] 中的一个）
                Action Input: 工具的输入参数
                Observation: 工具执行后的结果
                ...（可以重复）
                Thought: 我现在可以给出最终答案了
                Final Answer: 返回给用户的最终回答


                chat_history: {chat_history}
                Question: {input}
                Thought:{agent_scratchpad}
                """),
        }

        # 2. 创建各种工具和执行器
        self.tools = ToolManager().get_tools()
        self.agent_executor = self._create_agent_executor()
        # 3. 创建 RunnableWithMessageHistory 用于 Agent
        self.agent_with_history = RunnableWithMessageHistory(
            self.agent_executor,
            get_session_history=self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        #从本地加载对话记录
        self.history = self.get_session_history(self.session_id)
        for item in HistoryManager().get_solo_history(self.session_id):
            self.history.add_user_message(item['user_question'])
            self.history.add_ai_message(item['ai_response'])

    def _create_agent_executor(self):
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompts["search"],
        )
        return AgentExecutor(agent=agent, tools=self.tools, verbose=False,handle_parsing_errors=True)

    def get_session_history(self, session_id):
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]

    def _handle_normal_stream(self, input_dict: dict):#2.0版本
        """处理普通对话"""
        history = self.get_session_history(self.session_id)
        # 先添加用户消息
        history.add_user_message(input_dict["input"])
        chain = self.prompts["normal"] | self.llm
        response = ""
        for chunk in chain.stream({
            "input": input_dict["input"],
            "chat_history": history.messages
        }):
            content = chunk.content
            if content:
                response += content
                yield content  
        history.add_ai_message(response)

    def _handle_search_stream(self, input_dict: dict):
        """处理联网搜索"""
        config = {"configurable": {"session_id": self.session_id}}
        # 使用 stream 模式
        # try:
        for event in self.agent_with_history.stream(
            {"input": input_dict["input"]},
            config=config
        ):
            #调试：打印 event 结构（第一次运行时打开）
            print(f"Event keys: {list(event.keys())}")
            print(f"Event: {event}")

            # 1. 判断是否是工具调用开始：检查 'actions' 字段
            if "actions" in event and event["actions"]:
                action = event["actions"][0]
                tool_name = getattr(action, "tool", "未知工具")
                yield f"\n🔍 正在调用工具：{tool_name}\n"
                continue

            # 2. 判断是否是工具调用结束：检查 'steps' 中的 Observation
            if "steps" in event and event["steps"]:
                step = event["steps"][0]
                if hasattr(step, "tool_output") or hasattr(step, "observation"):
                    result=step.observation
                    # print(f"查询结果：{result}")
                    yield "✅ 已获取搜索结果，正在生成回答...\n\n"
                continue                   
            # 3. 判断是否是 LLM 生成中：检查 'messages' 中的 AIMessageChunk
            if "output" in event:
                result = event["output"]
                prompt = ChatPromptTemplate.from_messages([
                ("system", "你是一个优秀的助手，你需要一字不落的完整复述用户的内容，不允许增加或减少或修改任何内容。"),
                ("user", "{input}"),
                ])
                chain = prompt | self.llm
                for chunk in chain.stream({"input": result}):
                    yield chunk.content
        # except Exception as e:
        #     yield f"\n❌ 搜索过程中发生错误：{str(e)}"
        
    
    def _handle_rag_stream(self, input_dict: dict):
        """处理RAG流式输出（这里需要你集成你的向量数据库）"""
        answer = self.my_rag.answer_question(input_dict['input'],self.session_id,'course')
        for chunk in answer:
            if chunk["type"] == "rag":
                yield chunk["content"]
            if chunk["type"] == "answer":
                yield chunk["answer"]
    
    
    def _handle_upload_stream(self, input_dict: dict):
        """处理文件上传流式输出"""
        upload_files = input_dict.get("upload") if input_dict.get("upload") else []
        len_files = len(upload_files)
        for index,doc in enumerate(upload_files):
            yield f"正在上传第{index+1}/{len_files}个文件\n"
            upload_result = self.my_rag.upload_document(doc,self.session_id)
            yield upload_result['message'] + '\n'
        if not self.my_rag.get_user_documents(self.session_id):
            yield "请先上传文件！\n"
            return
        answer = self.my_rag.answer_question(input_dict['input'], self.session_id, 'user')
        for chunk in answer:
            if chunk['type'] == 'answer':
                yield chunk['answer']
            # elif chunk['type'] == 'sources':
            #     yield chunk['sources']              
        # yield "流式传输测试中\n"

    def chat_stream(self,input_dict:dict):
        """
        统一的聊天入口，支持流式输出（返回生成器）
        """
        # 1. 识别意图
        intent = input_dict["intention"]
        self.intention = intent
        print(f"[DEBUG] 意图识别为: {intent}")
        
        # 2. 根据意图调用对应的处理函数（流式）
        if intent == "normal":
            # ✅ 使用 yield from 把 _handle_normal 的每个 token 透传出去
            yield from self._handle_normal_stream({"input": input_dict["message"]})

        elif intent == "search":
            # 这里可以先 yield "正在搜索..."，再流式返回最终答案
            # yield "正在联网查询..."
            yield from self._handle_search_stream({"input": input_dict["message"]})

        elif intent == "rag":
            # yield "正在从知识库查找信息...\n"           
            yield from self._handle_rag_stream({"input": input_dict["message"]})

        elif intent == "upload":
            yield "正在处理上传的文件，请稍等...\n"
            yield from self._handle_upload_stream({"input": input_dict["message"],"upload":input_dict["upload"]})

        else:
            yield from self._handle_normal_stream({"input": input_dict["message"]})


if __name__ == "__main__":
    router = AgentRouter("lna01")
    while True:
        user_input = input("请输入你的问题：")
        if user_input.lower() in ["退出", "quit", "exit"]:
            break       
        print("助手回复: ")
        # ✅ 正确方式：遍历生成器，逐个接收 token
        for token in router.chat_stream({"intention": "normal", "message": user_input, "upload": None}):
            print(token, end="", flush=True)  # 实时打印，不带换行
        print()  # 回答结束后换行
        
# if __name__ == "__main__":
#     router = AgentRouter("lna01")
#     while True:
#         user_input = input("\n请输入你的问题：")
#         if user_input.lower() in ["退出", "quit", "exit"]:
#             break
#         try:
#             print("助手回复: ", end="", flush=True)
#             # ✅ 正确方式：遍历生成器，逐个接收 token
#             for token in router.chat_stream(user_input, upload=None):
#                 print(token, end="", flush=True)  # 实时打印，不带换行
#             print()  # 回答结束后换行
#         except Exception as e:
#             print(f"\n发生错误: {e}\n")
        