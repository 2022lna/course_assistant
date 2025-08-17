import os
import shutil

def clean_gradio_tmp():
    directory_path = "课程助手/user_uploads"   
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)     
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)  # 删除文件或符号链接
                print(f"已删除文件: {item_path}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)  # 删除整个文件夹
                print(f"已删除文件夹: {item_path}")
        except Exception as e:
            print(f"删除 {item_path} 失败: {e}")

# 调用函数
clean_gradio_tmp()