"""
GitHub Issue 发布脚本 — 将日报发布为 GitHub Issue
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from github import Github
from config import GITHUB_TOKEN, GITHUB_REPO, DATA_DIR


CATEGORY_ICONS = {
    "要闻": "🔥",
    "AI 动态": "🤖",
    "开发生态": "💻",
    "芯片硬件": "🔬",
    "量子前沿": "⚛️",
    "行业动态": "🏭",
    "前瞻传闻": "📡",
}


def format_issue_markdown(daily: dict) -> tuple:
    """将结构化日报转换为 GitHub Issue Markdown"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    title = f"AI + 硬件日报 — {date}"
    
    lines = []
    lines.append(f"# 🗞️ AI + 硬件日报 — {date}")
    lines.append("")
    
    if daily.get("summary"):
        lines.append(f"> {daily['summary']}")
        lines.append("")

    # 按分类分组
    cards = daily.get("cards", [])
    categories = {}
    for card in cards:
        cat = card.get("category", "其他")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(card)

    # 按分类顺序输出
    category_order = ["要闻", "AI 动态", "开发生态", "芯片硬件", "量子前沿", "行业动态", "前瞻传闻"]
    
    for cat in category_order:
        if cat not in categories:
            continue
        icon = CATEGORY_ICONS.get(cat, "📌")
        lines.append(f"## {icon} {cat}")
        lines.append("")
        
        for card in categories[cat]:
            stars = "⭐" * card.get("importance", 3)
            source = card.get("source", "")
            desc = card.get("description", "")
            
            lines.append(f"### {card['title']}")
            lines.append(f"{desc}")
            if source:
                lines.append(f"")
                lines.append(f"📰 来源: {source} | {stars}")
            lines.append("")

    # 未分类的
    if "其他" in categories:
        lines.append("## 📌 其他")
        lines.append("")
        for card in categories["其他"]:
            lines.append(f"### {card['title']}")
            lines.append(f"{card.get('description', '')}")
            lines.append("")

    lines.append("---")
    lines.append(f"*本日报由 AI 自动生成，信息仅供参考，以原始来源为准。*")
    
    return title, "\n".join(lines)


def publish_issue(daily: dict, dry_run: bool = False) -> str:
    """发布 GitHub Issue"""
    title, body = format_issue_markdown(daily)
    
    if dry_run:
        print(f"\n[DRY RUN] 标题: {title}")
        print(f"[DRY RUN] 正文长度: {len(body)} 字符")
        output_file = DATA_DIR / f"issue_preview_{daily.get('date', 'today')}.md"
        output_file.write_text(f"# {title}\n\n{body}", encoding="utf-8")
        print(f"[DRY RUN] 预览已保存: {output_file}")
        return "dry_run"

    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError("GITHUB_TOKEN 和 GITHUB_REPO 未设置")

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    
    issue = repo.create_issue(title=title, body=body)
    print(f"\n已发布 Issue: {issue.html_url}")
    print(f"编号: #{issue.number}")
    
    return issue.html_url


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    
    if not daily_file.exists():
        print(f"未找到日报数据: {daily_file}")
        sys.exit(1)
    
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    
    # 默认 dry run，加 --publish 参数才真正发布
    dry_run = "--publish" not in sys.argv
    publish_issue(daily, dry_run=dry_run)
