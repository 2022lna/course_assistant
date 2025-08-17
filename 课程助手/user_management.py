from langchain_community.utilities import SQLDatabase
import gradio as gr
# from ai_respond import AIRespond
class User:
    username = None  # 用于存储当前登录用户的用户名
    # ai_respond = AIRespond(None)
    def __init__(self):
      self.db = SQLDatabase.from_uri("sqlite:///课程助手/课程助手.db") #sqlite:///是固定连接方法 后面跟文件路径
      # -- 创建用户表
      self.db.run("""
              CREATE TABLE IF NOT EXISTS users (
                  username TEXT PRIMARY KEY NOT NULL,
                  password TEXT NOT NULL
            )"""
            )
    #注册用户
    def register_user(self,username: str, password: str):
        if username.strip() == "" or password.strip() == "":
            return False, "用户名和密码不能为空"
        result = self.db.run(
            # "SELECT username FROM users WHERE username = ?",
            # (username,)
            "SELECT username FROM users WHERE username = :username",
            parameters={"username": username}
        )
        # 检查用户是否已存在
        if result.strip():
            return False, f"注册失败，用户 '{username}' 已存在，请选择其他用户名"
            # raise ValueError(f"用户 '{username}' 已存在，请选择其他用户名")  
        # 注册新用户    
        self.db.run(
            # "INSERT INTO users (username, password) VALUES (?, ?)",
            # (username, password)
            "INSERT INTO users (username, password) VALUES (:username, :password)",
            parameters={"username": username, "password": password}
        )
        return True, "注册成功！"
       
    # 用户登录
    def login_user(self, username: str, password: str):
         # 查询匹配的用户名和密码
        result = self.db.run(
            # "SELECT username FROM users WHERE username = ? AND password = ?",
            # (username, password)
            "SELECT username FROM users WHERE username = :username AND password = :password",
            parameters={"username": username, "password": password}
        )
        
        # 如果查询结果不为空，说明登录成功
        if result.strip():
            self.username = username  # 用于聊天界面显示当前用户
            # self.ai_respond = AIRespond(username) #登陆成功更新回复ai
            return self.username, "登录成功!", gr.update(selected="chat")
        else:
            return None, "用户名或密码错误!",gr.update(selected="login")
    def logout_user(self):
        # print("点击了退出按钮")
        self.username = None
        # self.ai_respond = AIRespond(None)
        
        return None,gr.update(selected="login")

if __name__ == "__main__":  
    user= User()
    # print(user.register_user("lna01", "123"))
    # print(user.login_user("lna01", "1234"))
    print(user.login_user("lna01", "123"))
    print(user.username)  # 输出当前登录用户的用户名