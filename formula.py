import requests
from bs4 import BeautifulSoup
import csv
import re # 导入正则表达式，用于精准识别数字

url = "https://www.bbc.com/sport/formula1"
headers = {'User-Agent': 'Mozilla/5.0'}
filename = 'f1_news_perfect.csv'

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

boxes = soup.find_all("div", attrs={"data-testid": "promo"})
print(f"🕵️‍♂️ 搜索完成，一共抓到了 {len(boxes)} 条新闻！")

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