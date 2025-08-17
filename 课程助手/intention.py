from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import os
from dotenv import load_dotenv
load_dotenv(r"./lna.env")
class IntentionRecognizer:
  def __init__(self):
    self.llm = ChatOpenAI(
                model="qwen-max",
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
    self.prompt=ChatPromptTemplate.from_messages(
      [
        ("system","""你是一个意图识别小助手，请根据用户的提问识别用户的意图，并返回意图名称。
        1. 如果用户问的是你能回答的问题，请仅返回数字1。
        2. 如果用户想查询相关文档里的相关内容，请仅返回数字2。
        3. 如果用户想查询实时信息或者需要联网搜索的信息，请仅返回数字3。
        """),
        ("user", "{question}")
      ]
    )
  def choice_intent(self,upload,question: str):
    if upload  is not None:
      return 4 # 上传文件意图
    chain=LLMChain(llm=self.llm,prompt=self.prompt)
    return chain.invoke({'question':question})['text']
  
if __name__ == "__main__":
  recognizer = IntentionRecognizer()
  question = "请问你能回答什么问题？"
  intent = recognizer.choice_intent(None, question)
  print(f"问题: {question}\n识别的意图: {intent}")
  # 测试其他问题
  question2 = "请帮我查询一下最新的天气情况。"
  intent2 = recognizer.choice_intent(None, question2)
  print(f"问题: {question2}\n识别的意图: {intent2}")