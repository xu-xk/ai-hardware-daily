"""
LLM 日报生成脚本 — 调用 DeepSeek 生成结构化日报
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# 兼容直接运行和模块导入
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, DATA_DIR,
)


def build_news_text(items: list) -> str:
    """将采集到的新闻格式化为 LLM 输入文本"""
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"---\n新闻 #{i}")
        lines.append(f"标题: {item['title']}")
        lines.append(f"来源: {item['source']} ({item['lang']})")
        lines.append(f"链接: {item['link']}")
        if item.get("summary"):
            lines.append(f"摘要: {item['summary']}")
        lines.append("")
    return "\n".join(lines)


def generate_daily(items: list) -> dict:
    """调用 LLM 生成结构化日报"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未设置")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    news_text = build_news_text(items)
    user_prompt = USER_PROMPT_TEMPLATE.format(count=len(items), news_text=news_text)

    print(f"\n调用 LLM: {DEEPSEEK_MODEL}")
    print(f"输入新闻: {len(items)} 条")

    import re

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=8000,
            )

            raw_output = response.choices[0].message.content.strip()
            print(f"LLM 输出: {len(raw_output)} 字符 (尝试 {attempt+1}/3)")

            # 解析 JSON（处理可能的 markdown 代码块包裹）
            if raw_output.startswith("```"):
                raw_output = raw_output.split("\n", 1)[1] if "\n" in raw_output else raw_output
                if raw_output.endswith("```"):
                    raw_output = raw_output[:-3]
                raw_output = raw_output.strip()

            result = json.loads(raw_output)
            
            # 验证 cards 不为空
            cards = result.get('cards', [])
            if not cards or len(cards) == 0:
                print(f"[WARN] cards 为空 (尝试 {attempt+1}/3)，重试...")
                if attempt < 2:
                    continue
                else:
                    raise ValueError("LLM 返回的 cards 为空")
            
            print(f"解析成功: {len(cards)} 条新闻")
            break

        except json.JSONDecodeError as e:
            print(f"[WARN] JSON 解析失败 (尝试 {attempt+1}/3): {e}")
            if attempt == 2:
                # 最后一次尝试：尝试提取 JSON 部分
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    result = json.loads(json_match.group())
                    cards = result.get('cards', [])
                    if not cards or len(cards) == 0:
                        raise ValueError("LLM 返回的 cards 为空")
                else:
                    raise ValueError("无法从 LLM 输出中提取 JSON")

    # 确保日期字段
    result["date"] = datetime.now().strftime("%Y-%m-%d")
    
    # 保存结果
    output_file = DATA_DIR / f"daily_{result['date']}.json"
    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"日报已保存: {output_file}")
    print(f"共 {len(result.get('cards', []))} 条新闻")

    return result


if __name__ == "__main__":
    # 测试：加载今天的原始数据并生成日报
    today = datetime.now().strftime("%Y%m%d")
    raw_file = DATA_DIR / f"raw_{today}.json"
    
    if not raw_file.exists():
        print(f"未找到今日采集数据: {raw_file}")
        print("请先运行 collect_rss.py")
        sys.exit(1)
    
    items = json.loads(raw_file.read_text(encoding="utf-8"))
    result = generate_daily(items)
    print(json.dumps(result, ensure_ascii=False, indent=2))
