"""
原文图片抓取 — 提取 og:image 或首张大图
"""
import json
import sys
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR


def extract_article_image(url: str) -> str:
    """从文章页面提取 og:image 或首张大图"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        r = urllib.request.urlopen(req, timeout=10)
        html = r.read().decode('utf-8', errors='replace')
        
        # 1. 尝试 og:image
        og_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not og_match:
            og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.IGNORECASE)
        if og_match:
            return og_match.group(1)
        
        # 2. 尝试 twitter:image
        tw_match = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if tw_match:
            return tw_match.group(1)
        
        # 3. 尝试文章内第一张大图
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for img_url in img_matches:
            if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if 'logo' not in img_url.lower() and 'icon' not in img_url.lower() and 'avatar' not in img_url.lower():
                    if img_url.startswith('http'):
                        return img_url
        
        return ''
    except Exception as e:
        print(f"  提取失败: {e}")
        return ''


def download_image(url: str, output_path: str) -> bool:
    """下载图片"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        r = urllib.request.urlopen(req, timeout=15)
        data = r.read()
        
        # 至少 5KB 才算有效图片
        if len(data) < 5000:
            return False
        
        with open(output_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def fetch_all_images(daily: dict) -> dict:
    """为日报中每条新闻抓取原文图片"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    output_dir = DATA_DIR / f"images_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_map = {}  # card_index -> image_path
    
    for i, card in enumerate(cards):
        link = card.get('link', '')
        if not link:
            print(f"新闻 {i+1}: 无链接，跳过")
            continue
        
        print(f"新闻 {i+1}/{len(cards)}: {card['title'][:30]}...")
        
        # 提取图片 URL
        img_url = extract_article_image(link)
        if not img_url:
            print(f"  无图片")
            continue
        
        print(f"  图片: {img_url[:80]}...")
        
        # 下载图片
        img_path = str(output_dir / f"news_{i+1}.jpg")
        if download_image(img_url, img_path):
            image_map[str(i+1)] = img_path
            print(f"  OK: {Path(img_path).stat().st_size / 1024:.0f}KB")
        
        # 限制最多 8 张
        if i >= 7:
            break
    
    # 保存映射
    map_file = output_dir / "map.json"
    map_file.write_text(json.dumps(image_map, ensure_ascii=False), encoding="utf-8")
    print(f"\n图片抓取完成: {len(image_map)} 张")
    
    return image_map


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    fetch_all_images(daily)
