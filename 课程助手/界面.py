import gradio as gr
from user_management import User
from ai_respond import AIRespond
from history_management import HistoryManager
import os
import uuid
from datetime import date
# 创建可写的临时目录
os.makedirs("课程助手/gradio_tmp", exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = "课程助手/gradio_tmp"

MAX_SESSIONS = 10 # 最大会话数
# 更新顶部导航栏以及历史聊天记录的函数
def update_info(username):
    user_id = username if username else "访客"
    welcome_prompt = gr.update(value=[
                                        {"role": "assistant", "content": "欢迎使用lna的课程咨询助手！"},
                                        {"role": "assistant", "content": f"{user_id}您好！很高兴为你服务！"},
                                    ], label="课程咨询助手" )
    if username:
        history_manager = HistoryManager()
        # 获取用户的所有历史记录
        history = history_manager.get_all_history(username)
        today = date.today()
        chat = {}
        for item in history:
            date_ = (today -date.fromisoformat(item['last_response_date'])).days
            chat[item['chat_id']] = date_#键存储会话ID，值存储最后一次响应日期
        update_buttons = [[0] * MAX_SESSIONS for _ in range(3)]
        count_today,count_yesterday,count_last_week = MAX_SESSIONS-1,MAX_SESSIONS-1,MAX_SESSIONS-1
        for id,time in chat.items():
            if time >= 7:
                update_buttons[2][count_last_week] = id
                count_last_week -= 1
            elif time == 1:
                update_buttons[1][count_yesterday] = id
                count_yesterday -= 1
            else:
                update_buttons[0][count_today] = id
                count_today -= 1
        updates = []
        # 更新按钮状态
        for i in range(3):
            for occupied in update_buttons[i]:
                if occupied != 0:
                    updates.append(gr.update(visible=True))
                else:
                    updates.append(gr.update(visible=False))

        return gr.update(value=f"""
        <div style="background-color: #ffffff; padding: 10px; color: white; font-size: 22px;">
            <span>欢迎你, {username}!</span>
        </div>
        """),update_buttons,welcome_prompt,None,*updates,*updates  # 返回更新后的导航栏和按钮状态
    else:
        update_buttons = [[0] * MAX_SESSIONS for _ in range(3)]
        updates = []
        # 登出时关闭所有按钮
        for i in range(3*MAX_SESSIONS):
             updates.append(gr.update(visible=False))           
        return gr.update(value="""
        <div style="background-color: #ffffff; padding: 10px; color: white; font-size: 22px;">
            <span>欢迎你, 访客!请先登录以查看聊天记录。</span>
        </div>
        """),update_buttons,welcome_prompt,None,*updates,*updates  # 返回更新后的导航栏和按钮状态
    

# 定义左侧聊天记录区域（支持点击）
def chat_history_section():    
    with gr.Column() as chat_col:
        new_conversation_button = gr.Button("新建对话", variant="primary")
        gr.Markdown("### 📝 聊天记录")
        today_chat_buttons = []  # 用于存储今天的聊天按钮
        today_del_buttons = []  # 用于存储今天的删除按钮
        gr.Markdown("#### 今天")
        with gr.Row():
            for i in range(MAX_SESSIONS):
                # 创建多个按钮，初始不可见
                chat = gr.Button(f"💬会话 {MAX_SESSIONS-i}", variant="secondary", visible=False,scale=3,min_width= 250)
                delete = gr.Button("❌", variant="secondary", visible=False,scale=1,min_width= 50)  # 删除按钮
                today_chat_buttons.append(chat)  # 将按钮添加到列表中
                today_del_buttons.append(delete)  # 将删除按钮添加到列表中
        gr.Markdown("#### 昨天")
        yesterday_chat_buttons = []  # 用于存储昨天的聊天按钮
        yesterday_del_buttons = []  # 用于存储昨天的删除按钮
        with gr.Row():
            for i in range(MAX_SESSIONS):
                chat = gr.Button(f"💬会话 {MAX_SESSIONS-i}", variant="secondary", visible=False,scale=3,min_width= 250)
                delete = gr.Button("❌", variant="secondary", visible=False,scale=1,min_width= 50)  # 删除按钮
                yesterday_chat_buttons.append(chat)  # 将按钮添加到列表中
                yesterday_del_buttons.append(delete)  # 将删除按钮添加到列表中
        gr.Markdown("#### 前7天")
        last_week_chat_buttons = []  # 用于存储前7天的聊天按钮
        last_week_del_buttons = []  # 用于存储前7天的删除按钮
        with gr.Row():
            for i in range(MAX_SESSIONS):
                chat = gr.Button(f"💬会话 {MAX_SESSIONS-i}", variant="secondary", visible=False,scale=3,min_width= 250)
                delete = gr.Button("❌", variant="secondary", visible=False,scale=1,min_width= 50)  # 删除按钮
                last_week_chat_buttons.append(chat)  # 将按钮添加到列表中
                last_week_del_buttons.append(delete)  # 将删除按钮添加到列表中
        # 预先创建所有按钮，初始不可见
        chat_buttons = [today_chat_buttons, yesterday_chat_buttons, last_week_chat_buttons]
        del_buttons = [today_del_buttons, yesterday_del_buttons, last_week_del_buttons]
    return chat_col, new_conversation_button, chat_buttons, del_buttons  # 返回按钮列表用于绑定事件

# 定义右侧聊天窗口
def chat_window():
    return gr.Chatbot(
        value=[
            {"role": "assistant", "content": "欢迎使用lna的课程咨询助手！"},
            {"role": "assistant", "content": "同学您好！很高兴为你服务！"},
        ],
        height=500,
        label="课程咨询助手",
        type="messages"
    )

# 定义底部输入区域 (修改为使用 MultimodalTextbox)
def input_area():
    with gr.Row(equal_height=True):
        with gr.Column(scale=4):
            # 使用 MultimodalTextbox 替代原来的 Textbox 和 Files
            msg = gr.MultimodalTextbox(
                placeholder="请输入你的问题（支持上传文件）",
                show_label=False,
                file_types=[".pdf", ".docx", ".txt", ".pptx", ".html", ".ipynb"], # 限制文件类型
                file_count="multiple", # 允许多文件上传
                # lines=1, # 可以根据需要调整文本框行数
            )
            intention = gr.Radio(
                choices=["普通对话", "联网搜索", "课程咨询", "文件上传"],
                value="普通对话",  # 默认选中
                show_label=False,
                interactive=True,
                elem_classes="tag-selector",
            )
        # btn = gr.Button("发送", scale=1,visible=False)
    # 注意：MultimodalTextbox 内部处理文件，不再需要单独的 gr.Files 组件
    return msg, intention # 只返回 MultimodalTextbox, intention 

# 主界面构建函数
def main_interface():
    user= User()
    history_manager = HistoryManager()
    css = """
    .gradio-container {
        font-family: 'Arial', sans-serif;
    }
    /* 移除html-container的padding类影响 */
    .html-container.padding {
        padding: 0 !important;
    }
    
    .logout-btn {
    background-color: #e74c3c !important;
    color: white !important;
    width: 200px !important;
    height: 50px !important;
    font-size: 16px !important;
    margin: 0 auto !important;
    display: block !important;
    }    
    /* 左侧聊天记录区域样式 */
    .left-panel {
        overflow-y: auto; /* 启用垂直滚动 */
        height: 600px; /* 固定高度，与右侧一致 */
        min-width: 380px !important;
        flex-shrink: 0 !important;
    }
    """

    with gr.Blocks(css=css) as demo:
        user_id_state = gr.State(None)# 当前用户ID状态
        cur_chat_id = gr.State(None)  # 当前会话ID状态
        # ai_respond = gr.State(AIRespond(None))  # 当前AI响应对象状态
        chat_buttons_state = gr.State([[0] * MAX_SESSIONS for _ in range(3)])  # 存储聊天记录按钮状态
        gr.Markdown("## 👨‍🏫 💬+👩‍⚕️ 💡课程问答助手与医疗顾问")
        # 使用 Tabs
        with gr.Tabs() as tabs:
            # 注册页面
            # with gr.Tab("注册"):
            with gr.TabItem("注册", id="register"):
                with gr.Row():
                    username_input = gr.Textbox(label="用户名")
                    password_input = gr.Textbox(label="密码", type="password")
                    # email_input = gr.Textbox(label="邮箱")
                register_button = gr.Button("注册")
                register_output = gr.Textbox(label="注册结果")
                register_state = gr.State(None)
                # 注册事件
                register_button.click(
                    fn=user.register_user,
                    inputs=[username_input, password_input],
                    outputs=[register_state, register_output]
                )

            # 登录页面
            # with gr.Tab("登录"):
            with gr.TabItem("登录", id="login"):
                with gr.Row():
                    login_username = gr.Textbox(label="用户名")
                    login_password = gr.Textbox(label="密码", type="password")
                login_button = gr.Button("登录")
                login_output = gr.Textbox(label="登录结果")
                # 登录事件
                login_button.click(
                    fn=user.login_user,
                    inputs=[login_username, login_password],
                    outputs=[user_id_state, login_output, tabs]
                )
                # gr.update(selected="chat")

            # 聊天页面
            with gr.TabItem("聊天", id="chat"):
                with gr.Row():
                    # 顶部导航栏（动态更新）
                    top_nav_html = gr.HTML()
                    logout_button = gr.Button("退出",elem_classes="logout-btn",scale=0)
                logout_button.click(
                    fn=user.logout_user,
                    inputs=[],
                    outputs=[user_id_state, tabs])
                with gr.Row():
                    # 左侧聊天记录区域
                    with gr.Column(scale=1, elem_classes="left-panel") as left_col:
                        chat_col,new_conversation_button,chat_buttons,del_buttons = chat_history_section()
                        def add_session(occupied_list,user_id):
                            if user_id is None:
                                user_id = "访客"
                            for i, occupied in reversed(list(enumerate(occupied_list[0]))):
                                if occupied == 0:  # 找到第一个未占用的会话
                                    occupied_list[0][i] = uuid.uuid4()  # 标记为已占用并设置唯一会话id
                                    update_chatbot = gr.update(value=[
                                        {"role": "assistant", "content": "欢迎使用lna的课程咨询助手！"},
                                        {"role": "assistant", "content": f"{user_id}您好！很高兴为你服务！"},
                                    ], label="当前会话id: " + str(occupied_list[0][i]))
                                    update = []
                                    for j in range(MAX_SESSIONS):
                                        if j == i:  # 只显示当前会话按钮
                                            update.append(gr.update(visible=True))                                          
                                        else:
                                            update.append(gr.update())
                                    update = update + update
                                    return occupied_list, update_chatbot, occupied_list[0][i], *update  # 返回新会话和所有按钮状态
                             # 全部占用
                            raise gr.Error("已达最大会话数，无法创建更多会话！")                                                   

                    # 右侧聊天主窗口
                    with gr.Column(scale=5):
                        chatbot = chat_window()
                        # 使用修改后的 input_area
                        multimodal_input, intention = input_area() # 接收 MultimodalTextbox

                        # 回复函数 (修改以处理 MultimodalTextbox 的输出)
                        # MultimodalTextbox 的输出是一个 dict: {"text": "...", "files": [...]}
                        def respond_stream(multimodal_data, chat_history, intention_state,occupied_list, user_id,chat_id):
                            cur_chat_id = chat_id
                            update = []
                            for _ in range(MAX_SESSIONS):
                                update.append(gr.update())
                            update = update + update
                            user_text = multimodal_data.get("text", "")
                            user_files = multimodal_data.get("files", [])
                            print(f"用户输入文本: {user_text}")
                            print(f"上传的文件: {user_files}")
                            if user_text.strip() or user_files: # 检查是否有文本或文件
                                ai_respond = AIRespond(str(chat_id))
                                #新建一个对话
                                if cur_chat_id is None:
                                    occupied_list, update_chatbot, cur_chat_id, *update = add_session(occupied_list, user_id)
                                    update_chatbot = gr.update(label="当前会话id: " + str(cur_chat_id))
                                    yield {"text": "", "files": []}, update_chatbot, occupied_list, cur_chat_id, *update
                                    ai_respond = AIRespond(str(chat_id))
                                chat_history.append({"role": "user", "content": user_text}) # 可以考虑如何处理文件
                                chat_history.append({"role": "assistant", "content": ''})
                                yield {"text": "", "files": []}, chat_history, occupied_list, cur_chat_id,*update  # 清空输入框并刷新界面

                                # 2. 创建 AIRespond 实例
                                # ai_respond = user.ai_respond
                                # 3. 流式生成回复
                                bot_response = ""
                                # try:
                                # ✅ 调用流式方法，逐个接收 token
                                # 假设 ai_respond.respond_stream 可以处理文件列表
                                for token in ai_respond.respond_stream(user_files, user_text, intention_state):
                                    if token and token.strip():  # 避免空字符
                                        bot_response += token
                                        # 更新 chatbot 的最后一条消息
                                        chat_history[-1]={"role": "assistant", "content": bot_response}
                                        yield {"text": "", "files": []}, chat_history, occupied_list, cur_chat_id,*update  # 清空输入框并逐步更新界面
                                        # 添加对话到数据库
                                today = date.today()
                                history_manager.add_history({
                                    "chat_id": str(cur_chat_id),
                                    "user_id": user_id if user_id is not None else '访客',
                                    "user_question": user_text,
                                    "ai_response": bot_response,
                                    "last_response_date": today
                                })
                            else:
                                # 如果没有输入，也清空输入框
                                 yield {"text": "", "files": []}, chat_history, occupied_list, cur_chat_id,*update
                        # 绑定意图选择事件  
                        intent_state = gr.State("normal")
                        def process_choice(choice):
                            print(f"您选择了: {choice}")
                            intent_map = {
                                "联网搜索": "联网搜索",
                                "课程咨询": "课程咨询",
                                "文件上传": "文件上传"
                            }
                            return intent_map.get(choice, "normal")
                        intention.change(fn=process_choice,inputs=intention,outputs=intent_state)
                        
                        # 更新事件绑定，使用 MultimodalTextbox
                        # MultimodalTextbox.submit 会在用户按下 Enter 时触发
                        multimodal_input.submit(
                            fn=respond_stream,
                            inputs=[multimodal_input, chatbot, intent_state,chat_buttons_state,user_id_state,cur_chat_id], # 输入是 MultimodalTextbox 组件
                            outputs=[multimodal_input, chatbot,chat_buttons_state,cur_chat_id]+chat_buttons[0]+del_buttons[0] # 输出更新 MultimodalTextbox(清空) 和 Chatbot
                        )
                        #新建会话按钮点击事件               
                        new_conversation_button.click(
                            fn=add_session,  # 点击后显示新会话按钮,清空当前会话
                            inputs=[chat_buttons_state,user_id_state],  # 当前聊天记录按钮状态
                            outputs=[chat_buttons_state,chatbot,cur_chat_id]+chat_buttons[0]+del_buttons[0]  # 更新所有聊天按钮的可见性
                        )
                        # 绑定聊天记录按钮的点击事件
                        def load_chat_buttons(occupied_list,index, user_id):
                            i,j = index[0],index[1]
                            cur_chat_id = occupied_list[i][j]  # 获取对应的 UUID
                            # update_chatbot = gr.update(value=[{"role": "assistant", "content": f"加载会话 {uuid_str}"}],
                            #                             label="当前会话id: " + str(uuid_str))
                            user_id = user_id if user_id is not None else '访客'
                            chat_history = []
                            for item in history_manager.get_solo_history(str(cur_chat_id)):
                                chat_history.append({"role": "user", "content": item['user_question']})
                                chat_history.append({"role": "assistant", "content": item['ai_response']})
                            update_chatbot = gr.update(value=chat_history, label="当前会话id: " + str(cur_chat_id))
                            return  update_chatbot, cur_chat_id
                        def load_del_buttons(occupied_list,index,user_id,cur_chat_id):
                            i,j = index[0],index[1]
                            chat_id = occupied_list[i][j]  # 获取对应的 UUID
                            user_id = user_id if user_id is not None else '访客'
                            history_manager.delete_history(user_id,str(chat_id))
                            if j == 0:  
                                occupied_list[i][0] = 0
                            else:
                                occupied_list[i][1:j+1] = occupied_list[i][0:j]  # 删除当前会话
                                occupied_list[i][0] = 0  # 标记为未占用
                            updates = []
                            # 更新按钮状态
                            for occupied in occupied_list[i]:
                                if occupied != 0:
                                    updates.append(gr.update(visible=True))
                                else:
                                    updates.append(gr.update(visible=False))
                            # 返回更新后的状态和按钮
                            if chat_id == cur_chat_id:
                                welcome_prompt = gr.update(value=[
                                        {"role": "assistant", "content": "欢迎使用lna的课程咨询助手！"},
                                        {"role": "assistant", "content": f"{user_id}您好！很高兴为你服务！"},
                                    ], label="课程咨询助手" )
                                return occupied_list,welcome_prompt,None,*updates,*updates                           
                            return occupied_list,gr.update(),cur_chat_id,*updates,*updates
                            
                        for i in range(len(chat_buttons)):
                            for j in range(len(chat_buttons[i])):
                                chat_button = gr.State([i,j]) # 存储按钮的索引
                                # 绑定每个聊天按钮的点击事件
                                chat_buttons[i][j].click(
                                    fn=load_chat_buttons,
                                    inputs=[chat_buttons_state,chat_button,user_id_state],
                                    outputs=[chatbot,cur_chat_id]  # 更新状态
                                )                                                             
                                # 绑定删除按钮的点击事件
                                del_buttons[i][j].click(
                                    fn=load_del_buttons,
                                    inputs=[chat_buttons_state, chat_button,user_id_state,cur_chat_id],
                                    outputs=[chat_buttons_state,chatbot,cur_chat_id]+chat_buttons[i]+del_buttons[i] # 更新状态
                                )
                # 当页面加载或状态改变时更新导航栏
                demo.load(
                    fn=update_info,
                    inputs=[user_id_state],
                    outputs=[top_nav_html,chat_buttons_state,chatbot,cur_chat_id]
                    + chat_buttons[0]+chat_buttons[1]+chat_buttons[2]
                    + del_buttons[0]+del_buttons[1]+del_buttons[2]
                )
                user_id_state.change(
                    fn=update_info,
                    inputs=[user_id_state],
                    outputs=[top_nav_html,chat_buttons_state,chatbot,cur_chat_id]
                    + chat_buttons[0]+chat_buttons[1]+chat_buttons[2]
                    + del_buttons[0]+del_buttons[1]+del_buttons[2]  # 更新导航栏和按钮状态
                )
                



    return demo

# 启动应用
if __name__ == "__main__":
    demo = main_interface()
    demo.launch(share=True)