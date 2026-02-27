import requests
from bs4 import BeautifulSoup
import csv
import re
import os  # 第一步：一定要导入这个工具箱！

# 第二步：先定义名字，再使用它
url = "https://www.bbc.com/sport/formula1"
headers = {'User-Agent': 'Mozilla/5.0'}
filename = 'f1_news_perfect.csv'  # <--- 把它挪到这里！

# 第三步：这时候 Python 就认识 filename 了
old_titles = []
if os.path.exists(filename):
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        try:
            next(reader)  # 跳过表头
            for row in reader:
                if len(row) > 2:  # 确保这行有数据
                    old_titles.append(row[2]) # 假设标题在第三列
        except StopIteration:
            pass # 如果文件是空的，就跳过

response = requests.get(url, headers=headers)

# 🚪 在这里建立安全门
if response.status_code == 200:
    print("成功连接到 BBC！正在开始翻译网页...")
    soup = BeautifulSoup(response.text, "html.parser")
    # ... 这里放你之后的 boxes 抓取、循环和 CSV 写入代码 ...
    # 注意：所有在 if 里面的代码都要向右缩进（Indent）
else:
    # 如果门没开（比如返回了 404 或 403）
    print(f"糟糕，门没开！错误代码是：{response.status_code}")

boxes = soup.find_all("div", attrs={"data-testid": "promo"})

if not boxes:
    print("警报！没找到任何新闻盒子，可能是网页改版了！")
else:
    print(f"太棒了，抓到了 {len(boxes)} 条新闻！")
    # 开始你的 for 循环...

with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['发布时间', '类型/来源', '标题', '简讯'])
    
    for box in boxes:
        # --- A. 提取标题 ---
        # 寻找带有特定类名的标题，避免误抓
        title_tag = box.find("a")
        title = title_tag.get_text(strip=True) if title_tag else "无标题"
        
        # --- B. 提取简讯 ---
        # 💡 改进：指定类名 ssrcss-1q0x1qg-Paragraph，避免抓到标题里的文字
        summary_tag = box.find("p", class_="ssrcss-1q0x1qg-Paragraph")
        summary = summary_tag.get_text(strip=True) if summary_tag else "（此条为快讯/视频）"
        
        # 如果简讯和标题一模一样，说明抓错了，设为补充说明
        if summary == title:
            summary = "（点击进入查看详情）"
            
        # --- C. 精细化分拣元数据 ---
        metadata_spans = box.find_all("span", class_="ssrcss-61mhsj-MetadataText e4wm5bw1")
        
        post_time = "" # 1. 默认设置为空，不再显示“专题/汇总”
        other_info = []
        
        # 扩展时间关键词，包含月份和长效视频描述
        time_keywords = [
            "posted", "ago", "hours", "mins", "days", "year", "available",
            "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
        ]
        
        for span in metadata_spans:
            full_text = span.get_text(strip=True)
            text_lower = full_text.lower()
            
            # 过滤干扰项
            if "comment" in text_lower or "follow" in text_lower:
                continue
            
            # 检查是否包含时间相关的关键词
            is_time = any(word in text_lower for word in time_keywords)
            
            if is_time:
                # 2. 如果是时间，优先取“隐身”的干净版本（如 16 February）
                hidden_tag = span.find("span", class_="visually-hidden")
                if hidden_tag:
                    post_time = hidden_tag.get_text(strip=True)
                else:
                    # 如果没有隐身标签，为了防止 16 February16 Feb 这种重复，只取前半部分
                    # 这是一个小技巧：通常重复的部分长度较短
                    post_time = full_text[:len(full_text)//2] if len(full_text) > 10 else full_text
            else:
                # 3. 剩下的（如 Formula 1, BBC World Service）放入类型栏
                if full_text and not full_text.isdigit():
                    other_info.append(full_text)
        
        # 整理类型来源
        category_source = " | ".join(list(dict.fromkeys(other_info))) if other_info else "Formula 1"
        
        
        writer.writerow([post_time, category_source, title, summary])

print(f"✅ 任务完成！请检查最新的：{filename}")
# 核心分拣逻辑：通过关键词识别时间，并利用字符串切片和字典去重清洗数据。

new_stories = []
for box in boxes:
    # 提取标题 title ...
    if title not in existing_titles:
        new_stories.append({"title": title, "link": link})

# 3. 只有当 new_stories 不为空时，才执行写入和发邮件
if new_stories:
    print(f"检测到 {len(new_stories)} 条新消息，准备发送邮件...")
    
    # 构造邮件内容
    email_content = "最新围场消息：\n\n"
    for item in new_stories:
        email_content += f"【{item['title']}】\n链接：{item['link']}\n\n"

    # 发送邮件逻辑
    msg = MIMEText(email_content)
    msg['Subject'] = '🏎️ F1 围场最新消息提醒'
    msg['From'] = os.getenv('EMAIL_USER')
    msg['To'] = "你的接收邮箱@example.com"

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        server.send_message(msg)
    
    # 最后再更新 CSV 文件（覆盖旧的）
    # ... 之前的写入逻辑 ...
else:
    print("没有新内容，跳过提醒。")