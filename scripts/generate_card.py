"""
卡片生成脚本 — 日报 JSON → HTML → PNG
"""
import json
import sys
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DATA_DIR
from card_prompt import CARD_SYSTEM_PROMPT


def build_card_input(daily: dict) -> str:
    """将日报 JSON 格式化为 LLM 输入"""
    lines = []
    lines.append(f"主标题: {daily.get('mainTitle', 'AI + 硬件日报')}")
    lines.append(f"日期: {daily.get('date', '')}")
    lines.append(f"摘要: {daily.get('summary', '')}")
    lines.append("")
    
    for i, card in enumerate(daily.get("cards", []), 1):
        lines.append(f"---\n新闻 #{i}")
        lines.append(f"标题: {card['title']}")
        lines.append(f"描述: {card.get('description', '')}")
        lines.append(f"分类: {card.get('category', '')}")
        lines.append(f"图标: {card.get('icon', 'article')}")
        lines.append("")
    
    return "\n".join(lines)


def generate_html(daily: dict) -> str:
    """调用 LLM 生成卡片 HTML"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未设置")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    user_input = build_card_input(daily)

    print(f"调用 LLM 生成卡片 HTML...")

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": CARD_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.3,
                max_tokens=8000,
            )

            html = response.choices[0].message.content.strip()
            print(f"LLM 输出: {len(html)} 字符 (尝试 {attempt+1}/3)")

            # 清理 markdown 代码块
            if html.startswith("```"):
                html = html.split("\n", 1)[1] if "\n" in html else html
                if html.endswith("```"):
                    html = html[:-3]
                html = html.strip()

            # 提取纯 HTML（去掉 LLM 附加的解释文字）
            import re
            # 找到 <!DOCTYPE 或 <html 开始，到 </html> 结束
            html_match = re.search(r'(<!DOCTYPE[^>]*>|<html[\s\S]*</html>)', html, re.IGNORECASE)
            if html_match:
                html = html_match.group(0)
            elif '<html' in html.lower():
                # 如果有 <html 但没有配对的 </html>，截取到末尾
                idx = html.lower().index('<html')
                html = html[idx:]
            
            # 验证是有效 HTML
            if "<html" in html.lower() or "<!doctype" in html.lower():
                return html
            else:
                print(f"[WARN] 输出不是有效 HTML (尝试 {attempt+1}/3)")

        except Exception as e:
            print(f"[ERROR] LLM 调用失败 (尝试 {attempt+1}/3): {e}")

    raise ValueError("无法生成有效 HTML")


def render_png(html: str, output_path: str, width: int = 1920, height: int = 1080):
    """使用 Playwright 将 HTML 渲染为 PNG"""
    from playwright.sync_api import sync_playwright

    print(f"渲染 PNG: {width}x{height} -> {output_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = browser.new_page(viewport={'width': width, 'height': height})
        
        # 加载 HTML
        page.set_content(html, wait_until='networkidle')
        
        # 等待字体和样式加载
        page.wait_for_timeout(1000)
        
        # 截图
        page.screenshot(path=output_path, full_page=False)
        
        browser.close()

    print(f"PNG 已保存: {output_path}")


def generate_card(daily: dict) -> str:
    """完整流程：日报 JSON → HTML → PNG"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    # 1. 生成 HTML
    html = generate_html(daily)
    
    # 保存 HTML
    html_path = DATA_DIR / f"card_{date}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML 已保存: {html_path}")
    
    # 2. 渲染 PNG
    png_path = DATA_DIR / f"card_{date}.png"
    render_png(html, str(png_path))
    
    return str(png_path)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    
    if not daily_file.exists():
        print(f"未找到日报数据: {daily_file}")
        sys.exit(1)
    
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    png_path = generate_card(daily)
    print(f"\n卡片生成完成: {png_path}")
