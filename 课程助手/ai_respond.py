from agent_with_tools import AgentRouter
class AIRespond:
    def __init__(self,chat_id):
        self.router = AgentRouter(chat_id)  # 初始化路由器，传入会话ID
    def _route_intent(self, intention,upload=[]) -> str:
        """
            intention:用户输入的意图
            upload:用户上传的文件路径列表
            return:返回对应的意图名称包括(normal,search,rag,upload)
        """
        if upload:
            intent_code = "文件上传"
        else:
            intent_code = intention
        # 根据返回的数字代码映射到具体意图
        intent_map = {
            "联网搜索": "search",
            "课程咨询": "rag",
            "文件上传": "upload"  # 对应文件上传
        }
        
        # 返回对应的意图名称，如果无法识别则默认为 normal
        return intent_map.get(intent_code, "normal")
    
    def respond_stream(self, upload, message,choice):
        """
        流式响应：返回一个生成器，逐步产出 token
        供 Gradio 的 chatbot 使用
        """
        intention = self._route_intent(choice,upload)
        for token in self.router.chat_stream({"intention":intention,"upload":upload,"message":message}):
            yield token  # 把每个 token 向上传递给 Gradio       
