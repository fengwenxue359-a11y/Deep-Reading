import feedparser
from openai import OpenAI
import json
import os
import datetime

# ================= 精选深度内容源 =================
# 书籍/学术长文：JSTOR Daily, Farnam Street, The Marginalian
# 深度访谈播客：Lex Fridman, Huberman Lab
RSS_FEEDS = [
    {"name": "JSTOR Daily", "url": "https://daily.jstor.org/feed/"},
    {"name": "Farnam Street", "url": "https://fs.blog/feed/"},
    {"name": "The Marginalian", "url": "https://www.themarginalian.org/feed/"},
]

# 从环境变量读取 API Key（在GitHub Secrets中配置）
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def ai_process(text, title):
    """用AI精加工长文"""
    prompt = f"""
    你是一位资深知识主编。请对以下英文内容进行深度加工。
    标题：{title}
    内容：{text[:3000]}...

    请严格遵守以下格式输出JSON（不要多余文字）：
    {{
        "title_cn": "精准的中文标题",
        "intro": "150字的主编导读，说明为什么这篇文章值得一读",
        "core_points": ["核心观点1", "核心观点2", "核心观点3"],
        "golden_quote": "文章中最发人深省的一句原话（保留英文并翻译）",
        "full_text_cn": "全文高质量中文翻译（分段呈现，重点标出）"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        # 清理AI可能返回的markdown代码块标记
        if content.startswith("```json"):
            content = content[7:-3]
        return json.loads(content)
    except Exception as e:
        print(f"AI处理失败: {e}")
        return None

def generate_daily_deep_read():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    deep_items = []
    
    print("开始抓取深度内容...")
    for feed_info in RSS_FEEDS:
        feed = feedparser.parse(feed_info['url'])
        # 每天每个源只挑最新的一篇，保证质量
        for entry in feed.entries[:1]:
            print(f"正在处理: {feed_info['name']} - {entry.title}")
            # 提取全文（有些RSS包含全文，有些只有摘要，AI会基于提取到的内容工作）
            full_content = entry.get('summary', '')
            if 'content' in entry:
                full_content = entry.content[0].value
                
            processed = ai_process(full_content, entry.title)
            if processed:
                item = {
                    "source": feed_info["name"],
                    "original_link": entry.link,
                    **processed # 把AI处理好的字段合并进来
                }
                deep_items.append(item)

    data = {
        "date": today_str,
        "items": deep_items
    }
    
    os.makedirs("briefs/archive", exist_ok=True)
    with open("briefs/latest.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(f"briefs/archive/{today_str}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    archive_dir = "briefs/archive"
    history = sorted([f.replace('.json', '') for f in os.listdir(archive_dir) if f.endswith('.json')], reverse=True)
    with open("briefs/history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

    print(f"成功生成 {len(deep_items)} 篇深度长文。")

if __name__ == "__main__":
    generate_daily_deep_read()
