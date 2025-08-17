from langchain_community.utilities import SQLDatabase
class HistoryManager:   
    def __init__(self):

      self.db = SQLDatabase.from_uri("sqlite:///课程助手/课程助手.db") #sqlite:///是固定连接方法 后面跟文件路径
      # -- 创建用户表
      self.db.run("""
              CREATE TABLE IF NOT EXISTS chat_history (
                user_id TEXT NOT NULL, -- 用户ID
                chat_id TEXT NOT NULL, -- 会话ID                
                user_question TEXT NOT NULL, -- 用户问题
                ai_response TEXT NOT NULL, -- AI回答
                last_response_date DATE NOT NULL -- 最后回答时间
            );
            """
          )
    def add_history(self, input_dict: dict):
        self.db.run("""
            INSERT INTO chat_history (chat_id,user_id, user_question, ai_response, last_response_date)
            VALUES (:chat_id, :user_id, :user_question, :ai_response, :last_response_date)
        """, 
        parameters={
            "chat_id": input_dict["chat_id"],
            "user_id": input_dict["user_id"],
            "user_question": input_dict["user_question"],
            "ai_response": input_dict["ai_response"],
            "last_response_date": input_dict["last_response_date"]
        })
        print(f"[sql] 成功为用户{input_dict['user_id']}添加一次对话记录{input_dict['chat_id']}\n")

    def get_all_history(self, user_id: str):
        result = self.db._execute("""
          SELECT c.chat_id, c.last_response_date, c.user_question, c.ai_response 
          FROM chat_history AS c 
          WHERE c.user_id = :user_id
        """, 
        parameters={
            "user_id": user_id
        })
        print(f"[sql] 成功获取用户{user_id}的所有对话记录\n")
        return result


    def get_solo_history(self, chat_id: str):
        result = self.db._execute("""
          SELECT c.user_question, c.ai_response, c.last_response_date 
          FROM chat_history AS c 
          WHERE c.chat_id = :chat_id
        """, 
        parameters={
            "chat_id": chat_id
        })
        print(f"[sql] 成功获取会话{chat_id}的对话记录\n")
        return result       

    def delete_history(self, user_id: str, chat_id: str):
        self.db._execute("""
          DELETE FROM chat_history 
          WHERE chat_id = :chat_id AND user_id = :user_id
        """, 
        parameters={
            "chat_id": chat_id,
            "user_id": user_id
        })
        print(f"[sql] 成功删除用户{user_id}会话{chat_id}的对话记录\n")
    
from datetime import date
# today = date.today()
# print(today)  # 输出：2025-04-05
# print(type(today))  # <class 'datetime.date'>
import uuid
if __name__ == "__main__":
    history_manager = HistoryManager()
    chat_id = str(uuid.uuid4())  # 生成唯一的会话ID
    chat_id2 = str(uuid.uuid4())  # 生成另一个唯一的会话ID
    user_id = "user1"  # 假设用户ID为"user1"
    today = date.today()
    # # 添加历史记录示例
    # history_manager.add_history({
    #     "chat_id": chat_id,
    #     "user_id": user_id,
    #     "user_question": "你好",
    #     "ai_response": "你好, 有什么可以帮助你的吗？",
    #     "last_response_date": today
    # })
    # history_manager.add_history({
    #     "chat_id": chat_id2,
    #     "user_id": user_id,
    #     "user_question": "你好, 我想知道你是男是女",
    #     "ai_response": "你好, 我是男的",
    #     "last_response_date": today
    # })    
    # 获取所有历史记录示例
    all_history = history_manager.get_all_history(user_id)
    print(all_history)
    
    # # 获取单个会话的历史记录示例
    # solo_history = history_manager.get_solo_history(chat_id, user_id)
    # print(solo_history[0])
   
       
    

    # # 删除历史记录示例
    # history_manager.delete_history(user_id, chat_id)
