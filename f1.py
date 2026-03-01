import requests  # 导入网络请求工具，用于获取网页源代码
from bs4 import BeautifulSoup  # 导入网页解析工具，用于提取 HTML 数据
import csv  # 导入 CSV 工具，用于读写表格文件
import re  # 导入正则表达式工具，用于处理文本匹配
import os  # 导入系统工具，用于检查文件是否存在
import smtplib  # 导入邮件协议工具，负责发送邮件
from email.mime.text import MIMEText  # 导入邮件格式工具，用于编写邮件正文

# ==========================================
# 1. 基础配置（比赛发车位）
# ==========================================
url = "https://www.bbc.com/sport/formula1"  # 目标网址：BBC F1 频道
headers = {'User-Agent': 'Mozilla/5.0'}  # 伪装成浏览器，避免被网站拦截
filename = 'f1_news_perfect.csv'  # 存储数据的文件名

# 定义时间关键词，用于在复杂的网页标签中精准识别出“时间”
time_keywords = [
    "posted", "ago", "hours", "mins", "days", "year", "available",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
]

# ==========================================
# 2. 建立记忆（查看是否有旧数据）
# ==========================================
old_titles = set()  # 创建一个集合来存放旧标题（集合查找速度极快且自动去重）
if os.path.exists(filename):  # 如果 CSV 文件已经存在
    with open(filename, 'r', encoding='utf-8-sig') as f:  # 以读取模式打开文件
        reader = csv.reader(f)  # 创建阅读器
        try:
            next(reader)  # 跳过第一行的表头
            for row in reader:  # 遍历文件中的每一行
                if len(row) > 2:  # 确保这行数据完整（标题通常在第 3 列）
                    old_titles.add(row[2])  # 将旧标题存入集合，方便后面对比
        except StopIteration:  # 如果文件是空的，直接跳过
            pass

# ==========================================
# 3. 现场抓取（深入围场）
# ==========================================
response = requests.get(url, headers=headers)  # 向网站发送请求
if response.status_code == 200:  # 如果服务器返回 200（代表成功打开网页）
    print("成功连接到 BBC！正在解析数据...")
    soup = BeautifulSoup(response.text, "html.parser")  # 将网页源代码交给翻译官解析
else:
    print(f"门没开！错误代码：{response.status_code}")
    exit()  # 如果连接失败，直接结束程序

boxes = soup.find_all("div", attrs={"data-testid": "promo"})  # 找到网页中所有的新闻小盒子
current_scraped_data = []  # 准备一个篮子，装今天抓到的所有新闻
new_stories_for_email = []  # 准备另一个篮子，专门装旧记录里没有的“新鲜事”

for box in boxes:  # 开始逐个解剖新闻盒子
    # --- A. 提取标题与链接 ---
    a_tag = box.find("a")  # 在盒子里找链接标签 <a>
    title = a_tag.get_text(strip=True) if a_tag else "无标题"  # 提取文字，顺便剪掉多余空格
    raw_link = a_tag.get('href', '') if a_tag else ""  # 拿到原始链接
    link = f"https://www.bbc.com{raw_link}" if raw_link.startswith('/') else raw_link  # 补全 BBC 域名
    
    # --- B. 提取简讯 ---
    summary_tag = box.find("p", class_="ssrcss-1q0x1qg-Paragraph")  # 寻找特定类名的段落
    summary = summary_tag.get_text(strip=True) if summary_tag else "（点击查看详情）"
    
    # --- C. 处理时间与分类 ---
    metadata_spans = box.find_all("span", class_="ssrcss-61mhsj-MetadataText e4wm5bw1")
    post_time, other_info = "", []  # 初始化时间和分类变量
    
    for span in metadata_spans:  # 遍历盒子里的每个小零件
        full_text = span.get_text(strip=True)
        text_lower = full_text.lower()
        
        if "comment" in text_lower or "follow" in text_lower:
            continue  # 忽略“评论”或“关注”之类的干扰项
            
        is_time = any(word in text_lower for word in time_keywords)  # 检查是否有时间关键词
        if is_time:
            hidden_tag = span.find("span", class_="visually-hidden")  # 优先找隐藏的干净日期
            post_time = hidden_tag.get_text(strip=True) if hidden_tag else full_text[:len(full_text)//2]
        else:
            if full_text and not full_text.isdigit():  # 如果不是时间也不是纯数字，就是分类信息
                other_info.append(full_text)
    
    category = " | ".join(list(dict.fromkeys(other_info))) if other_info else "Formula 1"
    
    # --- D. 对比：这是新出的新闻吗？ ---
    if title not in old_titles and title != "无标题":
        new_stories_for_email.append({"title": title, "link": link})  # 放入待提醒篮子
    
    current_scraped_data.append([post_time, category, title, summary])  # 放入待保存篮子

# ==========================================
# 4. 智能提醒（有大事才发邮件）
# ==========================================
if new_stories_for_email:  # 如果新内容篮子里不为空
    print(f"发现 {len(new_stories_for_email)} 条新动态，正在发送提醒...")
    email_body = "🏎️ 围场前方有新消息：\n\n"
    for item in new_stories_for_email:
        email_body += f"【{item['title']}】\n🔗 传送门：{item['link']}\n\n"
    
    try:
        msg = MIMEText(email_body)  # 封装邮件内容
        msg['Subject'] = f'🔥 F1 实时更新：{len(new_stories_for_email)}条新资讯'
        msg['From'] = os.getenv('RECEIVER_EMAIL')  # 从环境变量读取发件人
        msg['To'] =os.getenv('RECEIVER_EMAIL')   # <--- 在这里填入你自己的邮箱

        with smtplib.SMTP_SSL('smtp.qq.com', 465) as server:  # 连接邮件服务器
            server.login(os.getenv('RECEIVER_EMAIL'), os.getenv('EMAIL_PASS'))  # 登录
            server.send_message(msg)  # 发送
        print("✅ 邮件已成功送达！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
else:
    print("💤 围场没有新动作，保持安静。")

# ==========================================
# 5. 更新档案（覆盖保存）
# ==========================================
with open(filename, 'w', encoding='utf-8-sig', newline='') as f:  # 使用 'w' 模式覆盖写入
    writer = csv.writer(f)
    writer.writerow(['发布时间', '类型/来源', '标题', '简讯'])  # 写下表头
    writer.writerows(current_scraped_data)  # 一口气写入今天抓到的所有数据

print(f"📊 实时档案已同步：{filename}")