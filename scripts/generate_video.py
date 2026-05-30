"""
视频生成 v3 — 橘鸦风格
结构：
1. 片头："AI 早报"超大字 + 日期
2. AI 总结页（卡片风格概览）
3. 逐条 AI 新闻：标题卡 + 详情卡
4. 硬件总结页
5. 逐条硬件新闻：标题卡 + 详情卡
"""
import json
import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from generate_card import render_png
from openai import OpenAI


def get_audio_duration(audio_path: str) -> float:
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def generate_tts(text: str, output_path: str, voice: str = "zh-CN-YunxiNeural"):
    import asyncio, edge_tts
    async def _gen():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    asyncio.run(_gen())


def make_title_html(date_str: str, weekday: str) -> str:
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap" rel="stylesheet" />
<style>
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fbf9f6;font-family:'Noto Sans SC',sans-serif}}
.container{{text-align:center}}
h1{{font-size:220px;font-weight:900;color:#c96442;margin:0 0 20px;line-height:1;letter-spacing:12px}}
.date{{font-size:28px;color:#ccc;font-weight:400;letter-spacing:4px}}
</style></head><body>
<div class="container"><h1>AI 早报</h1><div class="date">{date_str} {weekday}</div></div>
</body></html>'''


def make_summary_html(cards: list, title: str) -> str:
    colors = ['#c96442', '#e09f3e', '#335c67', '#9e2a2b']
    items = ''
    for i, c in enumerate(cards[:6]):
        color = colors[i % len(colors)]
        short = c['title'][:8]
        items += f'<div class="item"><span class="dot" style="background:{color}"></span><span class="txt">{short}</span></div>'
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fbf9f6;font-family:'Noto Sans SC',sans-serif}}
.box{{text-align:center}}
h1{{font-size:80px;font-weight:700;color:#c96442;margin:0 0 60px}}
.list{{display:flex;flex-direction:column;gap:24px;align-items:center}}
.item{{display:flex;align-items:center;gap:16px}}
.dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0}}
.txt{{font-size:36px;font-weight:600;color:#4a403a}}
</style></head><body>
<div class="box"><h1>{title}</h1><div class="list">{items}</div></div>
</body></html>'''


def make_title_card_html(card: dict, tag_color: str = '#c96442') -> str:
    title = card['title']
    desc = card.get('description', '')[:80]
    category = card.get('category', '要闻')
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fbf9f6;font-family:'Noto Sans SC',sans-serif}}
.card{{width:1600px;background:#fff;border-radius:32px;border:1px solid #dad8d4;box-shadow:0 10px 30px -10px rgba(74,64,58,0.1);display:flex;overflow:hidden}}
.accent{{width:8px;background:{tag_color};flex-shrink:0}}
.content{{flex:1;padding:60px 80px}}
.tag{{display:inline-block;background:{tag_color};color:#fff;font-size:20px;font-weight:700;padding:6px 20px;border-radius:8px;margin-bottom:24px}}
h2{{font-size:56px;font-weight:700;color:#2d2d2d;margin:0 0 20px;line-height:1.3}}
.desc{{font-size:28px;color:#666;line-height:1.6}}
</style></head><body>
<div class="card"><div class="accent"></div>
<div class="content"><div class="tag">{category}</div><h2>{title}</h2><div class="desc">{desc}</div></div>
</div></body></html>'''


def make_detail_html(card: dict, accent_color: str = '#335c67') -> str:
    title = card['title'][:20]
    desc = card.get('description', '')
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fbf9f6;font-family:'Noto Sans SC',sans-serif}}
.card{{width:1600px;background:#fff;border-radius:32px;border:1px solid #dad8d4;box-shadow:0 10px 30px -10px rgba(74,64,58,0.1);display:flex;overflow:hidden}}
.accent{{width:8px;background:{accent_color};flex-shrink:0}}
.content{{flex:1;padding:60px 80px}}
h3{{font-size:36px;font-weight:700;color:{accent_color};margin:0 0 32px}}
p{{font-size:26px;color:#444;line-height:1.8;margin:0 0 16px}}
p strong{{color:#c96442}}
</style></head><body>
<div class="card"><div class="accent"></div>
<div class="content"><h3>关键信息</h3><p>{desc}</p></div>
</div></body></html>'''


def images_to_video(image_durations: list, output_path: str):
    concat_content = ""
    for img_path, duration in image_durations:
        concat_content += f"file '{img_path}'\n"
        concat_content += f"duration {duration:.2f}\n"
    concat_content += f"file '{image_durations[-1][0]}'\n"
    
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        f.write(concat_content)
    
    temp_video = output_path + ".temp.mp4"
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25', temp_video], capture_output=True)
    return temp_video, concat_file


def merge_audio(audio_paths: list, output_path: str):
    concat_content = ""
    silence_files = []
    for i, audio_path in enumerate(audio_paths):
        concat_content += f"file '{audio_path}'\n"
        if i < len(audio_paths) - 1:
            silence_path = output_path + f".silence_{i}.mp3"
            subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                           '-t', '0.5', '-q:a', '9', '-acodec', 'libmp3lame', silence_path], capture_output=True)
            concat_content += f"file '{silence_path}'\n"
            silence_files.append(silence_path)
    
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        f.write(concat_content)
    
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                    '-acodec', 'libmp3lame', '-b:a', '192k', output_path], capture_output=True)
    
    for sf in silence_files:
        Path(sf).unlink(missing_ok=True)
    Path(concat_file).unlink(missing_ok=True)


def generate_video(daily: dict) -> str:
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    if not cards:
        raise ValueError("日报没有新闻内容")
    
    ai_cards = [c for c in cards if c.get('category') in ['要闻', 'AI动态', '开发生态', '行业动态', '前瞻传闻']]
    hw_cards = [c for c in cards if c.get('category') in ['芯片硬件', '量子前沿']]
    if not ai_cards: ai_cards = cards[:5]
    if not hw_cards: hw_cards = cards[5:8] if len(cards) > 5 else []
    
    output_dir = DATA_DIR / f"video_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_segments = []
    weekday_map = {0:'一',1:'二',2:'三',3:'四',4:'五',5:'六',6:'日'}
    dt = datetime.strptime(date, "%Y-%m-%d")
    weekday = weekday_map[dt.weekday()]
    date_display = f"{dt.month}月{dt.day}号"
    
    # 1. 片头
    print("片头...")
    img = str(output_dir / "00_title.png")
    render_png(make_title_html(date_display, f"星期{weekday}"), img)
    audio = str(output_dir / "00_title.mp3")
    generate_tts(f"各位晚上好，今天是{date_display}星期{weekday}", audio)
    all_segments.append((img, audio, get_audio_duration(audio) + 1.0))
    
    # 2. AI 总结
    print("AI 总结...")
    img = str(output_dir / "01_ai_summary.png")
    render_png(make_summary_html(ai_cards, "今日 AI 大事"), img)
    audio = str(output_dir / "01_ai_summary.mp3")
    summary_text = "；".join([c['title'] for c in ai_cards[:5]])
    generate_tts(f"这是今日的AI大事。{summary_text}", audio)
    all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
    
    # 3. AI 新闻（每条：标题卡 + 详情卡）
    colors = ['#c96442', '#e09f3e', '#335c67', '#9e2a2b']
    for i, card in enumerate(ai_cards):
        color = colors[i % len(colors)]
        print(f"AI {i+1}/{len(ai_cards)}: {card['title'][:25]}...")
        
        # 标题卡
        img = str(output_dir / f"ai_{i+1}_title.png")
        render_png(make_title_card_html(card, color), img)
        audio = str(output_dir / f"ai_{i+1}_title.mp3")
        generate_tts(card['title'], audio)
        all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
        
        # 详情卡
        img = str(output_dir / f"ai_{i+1}_detail.png")
        render_png(make_detail_html(card, color), img)
        audio = str(output_dir / f"ai_{i+1}_detail.mp3")
        generate_tts(card.get('description', card['title']), audio)
        all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
    
    # 4. 硬件
    if hw_cards:
        print("硬件总结...")
        img = str(output_dir / "02_hw_summary.png")
        render_png(make_summary_html(hw_cards, "硬件前沿"), img)
        audio = str(output_dir / "02_hw_summary.mp3")
        hw_text = "；".join([c['title'] for c in hw_cards])
        generate_tts(f"接下来是硬件领域的重要进展。{hw_text}", audio)
        all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
        
        for i, card in enumerate(hw_cards):
            color = colors[i % len(colors)]
            print(f"硬件 {i+1}/{len(hw_cards)}: {card['title'][:25]}...")
            
            img = str(output_dir / f"hw_{i+1}_title.png")
            render_png(make_title_card_html(card, color), img)
            audio = str(output_dir / f"hw_{i+1}_title.mp3")
            generate_tts(card['title'], audio)
            all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
            
            img = str(output_dir / f"hw_{i+1}_detail.png")
            render_png(make_detail_html(card, color), img)
            audio = str(output_dir / f"hw_{i+1}_detail.mp3")
            generate_tts(card.get('description', card['title']), audio)
            all_segments.append((img, audio, get_audio_duration(audio) + 0.5))
    
    # 合成
    print(f"\n合成视频: {len(all_segments)} 片段...")
    image_durations = [(s[0], s[2]) for s in all_segments]
    temp_video, concat_file = images_to_video(image_durations, str(output_dir / f"daily_{date}.mp4"))
    
    merged_audio = str(output_dir / f"daily_{date}_audio.mp3")
    merge_audio([s[1] for s in all_segments], merged_audio)
    
    final_video = DATA_DIR / f"daily_{date}.mp4"
    result = subprocess.run(['ffmpeg', '-y', '-i', temp_video, '-i', merged_audio,
                            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(final_video)],
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr[:300]}")
        raise RuntimeError("视频合成失败")
    
    Path(temp_video).unlink(missing_ok=True)
    Path(concat_file).unlink(missing_ok=True)
    Path(merged_audio).unlink(missing_ok=True)
    
    duration = get_audio_duration(str(final_video))
    size = final_video.stat().st_size
    print(f"\n完成: {final_video} | {duration:.1f}s | {size/1024/1024:.1f}MB")
    return str(final_video)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily = json.loads(open(DATA_DIR / f"daily_{date}.json", encoding="utf-8").read())
    generate_video(daily)
