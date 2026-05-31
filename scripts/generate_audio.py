"""
TTS 音频生成 — 使用 edge-tts（免费，中文效果好）
"""
import json
import sys
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR


async def generate_audio_edge(text: str, output_path: str, voice: str = "zh-CN-YunxiNeural"):
    """使用 edge-tts 生成音频"""
    import edge_tts
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_all_audio(daily: dict) -> list:
    """为日报中每条新闻生成 TTS 音频"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    if not cards:
        raise ValueError("日报没有新闻内容")
    
    output_dir = DATA_DIR / f"audio_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    audio_paths = []
    
    for i, card in enumerate(cards):
        # 构建 TTS 文本：标题 + 描述
        title = card["title"]
        desc = card.get("description", "")
        text = f"{title}。{desc}"
        
        audio_path = output_dir / f"news_{i+1}.mp3"
        
        print(f"生成音频 {i+1}/{len(cards)}: {title[:30]}...")
        
        try:
            asyncio.run(generate_audio_edge(text, str(audio_path)))
            audio_paths.append(str(audio_path))
            print(f"  OK: {audio_path.name}")
        except Exception as e:
            print(f"  FAIL: {e}")
    
    print(f"\n共生成 {len(audio_paths)} 个音频文件")
    return audio_paths


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    
    if not daily_file.exists():
        print(f"未找到日报数据: {daily_file}")
        sys.exit(1)
    
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    generate_all_audio(daily)
