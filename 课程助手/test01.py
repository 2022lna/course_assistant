from datetime import date
today = date.today()
# date = today.strftime("%Y-%m-%d")
#将字符串转为date对象
date_ = date.fromisoformat('2025-08-05')
print((today-date_).days)