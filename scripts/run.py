"""
AI + 硬件日报 — 主入口
用法:
  python run.py              # 完整流程：采集 → 生成 → 发布(dry run)
  python run.py --publish    # 完整流程：采集 → 生成 → 真正发布
  python run.py --collect    # 仅采集
  python run.py --generate   # 仅生成（需已有采集数据）
  python run.py --preview    # 仅预览 Issue（需已有日报数据）
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from collect_rss import collect_all, mark_as_used
from generate_daily import generate_daily
from generate_card import generate_card
from generate_video import generate_video
from publish_issue import publish_issue
from config import DATA_DIR


def main():
    args = set(sys.argv[1:])
    publish = "--publish" in args
    collect_only = "--collect" in args
    generate_only = "--generate" in args
    preview_only = "--preview" in args
    date = datetime.now().strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y%m%d")

    # ── Step 1: 采集 ──
    if not generate_only and not preview_only:
        print("\n" + "=" * 60)
        print("  Step 1: RSS 采集")
        print("=" * 60)
        items = collect_all()
        
        if not items:
            print("[WARN] 未采集到任何新闻，退出")
            return
        
        print(f"\n采集到 {len(items)} 条新闻")
        
        if collect_only:
            print("[collect 模式] 仅采集，退出")
            return
    else:
        # 加载已有数据
        raw_file = DATA_DIR / f"raw_{today}.json"
        if not raw_file.exists():
            print(f"[ERROR] 未找到采集数据: {raw_file}")
            sys.exit(1)
        items = json.loads(raw_file.read_text(encoding="utf-8"))
        print(f"加载已有采集数据: {len(items)} 条")

    # ── Step 2: LLM 生成 ──
    if not preview_only:
        print("\n" + "=" * 60)
        print("  Step 2: LLM 生成日报")
        print("=" * 60)
        daily = generate_daily(items)
        
        if generate_only:
            print("[generate 模式] 仅生成，退出")
            return
    else:
        # 加载已有日报
        daily_file = DATA_DIR / f"daily_{date}.json"
        if not daily_file.exists():
            print(f"[ERROR] 未找到日报数据: {daily_file}")
            sys.exit(1)
        daily = json.loads(daily_file.read_text(encoding="utf-8"))

    # ── Step 3: 生成封面卡片 ──
    print("\n" + "=" * 60)
    print("  Step 3: 生成封面卡片")
    print("=" * 60)
    try:
        png_path = generate_card(daily)
        print(f"封面卡片: {png_path}")
    except Exception as e:
        print(f"[WARN] 封面卡片生成失败: {e}")
        png_path = None

    # ── Step 4: 生成多卡片 + 音频 + 视频 ──
    video_path = None
    print("\n" + "=" * 60)
    print("  Step 4: 生成视频")
    print("=" * 60)
    try:
        # 视频只取 top 5 新闻
        video_daily = dict(daily)
        video_daily['cards'] = daily.get('cards', [])[:5]
        card_paths = generate_all_cards(video_daily)
        audio_paths = generate_all_audio(video_daily)
        video_path = generate_video(video_daily, card_paths, audio_paths)
        print(f"视频: {video_path}")
    except Exception as e:
        print(f"[WARN] 视频生成失败: {e}")

    # ── Step 5: 发布 ──
    print("\n" + "=" * 60)
    print(f"  Step 5: 发布 Issue {'(正式)' if publish else '(预览)'}")
    print("=" * 60)
    result = publish_issue(daily, dry_run=not publish, card_path=png_path)

    # ── 标记已使用 ──
    if publish:
        mark_as_used(items)
        print("\n✅ 日报已发布并标记已使用新闻")
    else:
        print(f"\n📋 预览模式，加 --publish 参数正式发布")

    # ── 输出摘要 ──
    cards = daily.get("cards", [])
    print(f"\n📊 今日日报: {len(cards)} 条新闻")
    for card in cards:
        cat = card.get("category", "")
        stars = "⭐" * card.get("importance", 3)
        print(f"  {stars} [{cat}] {card['title']}")


if __name__ == "__main__":
    main()
