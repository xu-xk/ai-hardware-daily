"""
橘鸦卡片生成器 — 调用 juya-news-card 的 generate.ts
"""
import json
import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR

# juya-news-card 项目路径
JUYA_DIR = Path(__file__).parent.parent / "juya-news-card"


def generate_card_for_news(news_text: str, output_dir: str) -> str:
    """为一条新闻生成卡片 PNG"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 调用 npm run generate
    cmd = f'npm run generate "{news_text}"'
    result = subprocess.run(
        cmd,
        cwd=str(JUYA_DIR),
        capture_output=True,
        text=True,
        timeout=120,
        shell=True,
    )
    
    if result.returncode != 0:
        print(f"  生成失败: {result.stderr[:200]}")
        return ""
    
    # 找到最新的输出目录
    output_dirs = sorted(JUYA_DIR.glob("output/news-*"), key=lambda x: x.stat().st_mtime)
    if not output_dirs:
        print(f"  未找到输出目录")
        return ""
    
    latest_dir = output_dirs[-1]
    screenshot = latest_dir / "screenshot.png"
    
    if not screenshot.exists():
        print(f"  未找到截图")
        return ""
    
    # 复制到目标目录
    import shutil
    target = output_path / f"card.png"
    shutil.copy2(str(screenshot), str(target))
    
    # 清理 juya-news-card 的输出目录
    for d in output_dirs:
        shutil.rmtree(str(d), ignore_errors=True)
    
    return str(target)


def generate_all_cards(daily: dict) -> list:
    """为日报中每条新闻生成卡片"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    output_dir = DATA_DIR / f"juya_cards_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    card_paths = []
    
    for i, card in enumerate(cards):
        title = card["title"]
        desc = card.get("description", "")
        text = f"{title}。{desc}"
        
        print(f"生成卡片 {i+1}/{len(cards)}: {title[:30]}...")
        
        # 为每条新闻创建单独的输出目录
        item_dir = output_dir / f"news_{i+1}"
        card_path = generate_card_for_news(text, str(item_dir))
        
        if card_path:
            card_paths.append(card_path)
            print(f"  OK: {Path(card_path).stat().st_size / 1024:.0f}KB")
        else:
            print(f"  FAIL")
    
    print(f"\n共生成 {len(card_paths)} 张卡片")
    return card_paths


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    
    # 只取前 3 条测试
    daily["cards"] = daily["cards"][:3]
    
    card_paths = generate_all_cards(daily)
    print(f"\n卡片路径: {card_paths}")
