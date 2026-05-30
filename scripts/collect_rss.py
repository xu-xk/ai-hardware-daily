"""
RSS 采集脚本 — 从多个信息源抓取并去重
"""
import feedparser
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import RSS_SOURCES, EXCLUDE_KEYWORDS, HARDWARE_KEEP_KEYWORDS, HISTORY_FILE, DATA_DIR


def load_history() -> set:
    """加载已处理的新闻 hash，用于去重"""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            # 只保留最近 7 天的记录
            cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            return {h for h in data if h >= cutoff} if isinstance(data, set) else set()
        except Exception:
            return set()
    return set()


def save_history(history: set):
    """保存已处理的新闻 hash"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(list(history), ensure_ascii=False), encoding="utf-8")


def compute_hash(title: str, link: str) -> str:
    """计算新闻唯一 hash"""
    content = f"{title.strip().lower()}|{link.strip().lower()}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def is_excluded(title: str, summary: str) -> bool:
    """检查是否应排除（消费电子水文）"""
    text = f"{title} {summary}".lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            # 如果同时包含硬件保留关键词，则不排除
            for keep_kw in HARDWARE_KEEP_KEYWORDS:
                if keep_kw.lower() in text:
                    return False
            return True
    return False


def is_recent(entry, hours: int = 48) -> bool:
    """检查是否在最近 N 小时内"""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return True  # 无法判断时间的默认保留
    entry_time = datetime(*published[:6], tzinfo=timezone.utc)
    return entry_time > datetime.now(timezone.utc) - timedelta(hours=hours)


def clean_html(text: str) -> str:
    """去除 HTML 标签"""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:500]  # 截断过长内容


def parse_single_feed(source: dict, timeout: int = 15) -> list:
    """解析单个 RSS 源"""
    items = []
    try:
        feed = feedparser.parse(
            source["url"],
            request_headers={"User-Agent": "Mozilla/5.0 (compatible; AIHardwareDaily/1.0)"}
        )
        if feed.bozo and not feed.entries:
            print(f"  [WARN] {source['name']}: 解析异常 - {feed.bozo_exception}")
            return []

        for entry in feed.entries[:20]:  # 每个源最多取 20 条
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            
            if not title or not link:
                continue

            # 去重
            news_hash = compute_hash(title, link)

            # 过滤消费电子
            if is_excluded(title, summary):
                continue

            items.append({
                "hash": news_hash,
                "title": title,
                "link": link,
                "summary": summary,
                "source": source["name"],
                "source_category": source["category"],
                "lang": source["lang"],
                "weight": source.get("weight", 1),
                "published": entry.get("published", ""),
            })

        print(f"  [OK] {source['name']}: {len(items)} 条有效新闻")
    except Exception as e:
        print(f"  [FAIL] {source['name']}: {e}")
    
    return items


def collect_all(hours: int = 48) -> list:
    """采集所有 RSS 源"""
    all_items = []
    history = load_history()
    
    print(f"\n{'='*50}")
    print(f"  开始采集 RSS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  历史记录: {len(history)} 条")
    print(f"{'='*50}\n")

    for group_name, sources in RSS_SOURCES.items():
        print(f"[{group_name}]")
        for source in sources:
            items = parse_single_feed(source)
            for item in items:
                if item["hash"] not in history:
                    all_items.append(item)
            time.sleep(0.5)  # 礼貌间隔

    # 按权重排序（高权重在前）
    all_items.sort(key=lambda x: x.get("weight", 1), reverse=True)

    # 去重（同标题不同源）
    seen_titles = set()
    unique_items = []
    for item in all_items:
        title_key = re.sub(r'\s+', '', item["title"].lower())[:30]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_items.append(item)

    print(f"\n采集完成: 原始 {len(all_items)} 条 → 去重后 {len(unique_items)} 条")

    # 保存到文件
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_file = DATA_DIR / f"raw_{datetime.now().strftime('%Y%m%d')}.json"
    output_file.write_text(
        json.dumps(unique_items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"已保存: {output_file}")

    return unique_items


def mark_as_used(items: list):
    """将已使用的新闻标记为已处理"""
    history = load_history()
    for item in items:
        history.add(item["hash"])
    save_history(history)


if __name__ == "__main__":
    items = collect_all()
    print(f"\n共采集 {len(items)} 条待处理新闻")
