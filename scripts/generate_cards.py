"""
多卡片生成 — 每条新闻一张卡片图
"""
import json
import sys
import re
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DATA_DIR
from card_prompt import CARD_SYSTEM_PROMPT
from generate_card import render_png


SINGLE_CARD_PROMPT = """你是一位顶尖的前端开发 AI。你的任务是根据提供的单条新闻，生成一个用于截图的、视觉平衡的单页 HTML。

**重要：仅输出 HTML 代码，不要输出任何解释性文字。**

**核心目标**
* 固定视图：精确渲染在 `1920x1080px` 画布上，**无滚动条**。
* 单条新闻大卡片：居中显示，信息清晰。
* 视觉风格：温暖米白背景、白色卡片、暖色点缀。

**单条新闻卡片结构**
* 主标题：AI + 硬件日报
* 副标题：日期
* 一张大卡片：图标 + 标题 + 详细描述（比整日报版本更详细，100-200字）

**代码资源**（同日报卡片，使用相同 CDN 和 CSS）

输出完整 HTML5 文档，以 `<!DOCTYPE html>` 开头，以 `</html>` 结尾。
"""


def generate_single_card_html(news_item: dict, date: str) -> str:
    """为单条新闻生成卡片 HTML"""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    user_input = f"""新闻标题: {news_item['title']}
新闻描述: {news_item.get('description', '')}
分类: {news_item.get('category', '')}
图标: {news_item.get('icon', 'article')}
日期: {date}"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SINGLE_CARD_PROMPT},
            {"role": "user", "content": user_input},
        ],
        temperature=0.3,
        max_tokens=6000,
    )

    html = response.choices[0].message.content.strip()
    
    # Clean markdown code block
    if html.startswith("```"):
        html = html.split("\n", 1)[1] if "\n" in html else html
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()
    
    return html


def generate_all_cards(daily: dict) -> list:
    """为日报中每条新闻生成卡片图"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    if not cards:
        raise ValueError("日报没有新闻内容")
    
    output_dir = DATA_DIR / f"cards_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    png_paths = []
    
    for i, card in enumerate(cards):
        print(f"生成卡片 {i+1}/{len(cards)}: {card['title'][:30]}...")
        
        try:
            html = generate_single_card_html(card, date)
            
            # Save HTML
            html_path = output_dir / f"news_{i+1}.html"
            html_path.write_text(html, encoding="utf-8")
            
            # Render PNG
            png_path = output_dir / f"news_{i+1}.png"
            render_png(html, str(png_path))
            
            png_paths.append(str(png_path))
            print(f"  OK: {png_path.name}")
            
        except Exception as e:
            print(f"  FAIL: {e}")
    
    print(f"\n共生成 {len(png_paths)} 张卡片图")
    return png_paths


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    
    if not daily_file.exists():
        print(f"未找到日报数据: {daily_file}")
        sys.exit(1)
    
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    generate_all_cards(daily)
