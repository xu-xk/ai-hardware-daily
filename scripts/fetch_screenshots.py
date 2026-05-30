"""
原文截图抓取 — 用 Playwright 截取原始新闻页面
"""
import json
import sys
import os
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR


def fetch_article_screenshot(url: str, output_path: str, width: int = 1200, height: int = 800):
    """截取原文页面"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = browser.new_page(viewport={'width': width, 'height': height})
        
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2000)  # 等待图片加载
            
            # 截取首屏
            page.screenshot(path=output_path, full_page=False)
            print(f"  截图: {output_path}")
        except Exception as e:
            print(f"  截图失败: {e}")
        finally:
            browser.close()


def fetch_all_screenshots(daily: dict) -> dict:
    """为日报中每条新闻抓取原文截图"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    output_dir = DATA_DIR / f"screenshots_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    screenshot_map = {}  # card_index -> screenshot_path
    
    for i, card in enumerate(cards):
        link = card.get('link', '')
        if not link:
            print(f"新闻 {i+1}: 无链接，跳过截图")
            continue
        
        print(f"新闻 {i+1}/{len(cards)}: {card['title'][:30]}...")
        
        # 截图
        img_path = str(output_dir / f"news_{i+1}.png")
        fetch_article_screenshot(link, img_path)
        
        if Path(img_path).exists():
            screenshot_map[str(i+1)] = img_path
        
        # 限制：最多截 8 张（避免太慢）
        if i >= 7:
            break
    
    # 保存映射
    map_file = output_dir / "map.json"
    map_file.write_text(json.dumps(screenshot_map, ensure_ascii=False), encoding="utf-8")
    print(f"\n截图完成: {len(screenshot_map)} 张")
    
    return screenshot_map


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    fetch_all_screenshots(daily)
