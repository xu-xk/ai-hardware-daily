"""
视频生成 v2 — 按橘鸦风格结构化
结构：
1. 片头：AI + 硬件日报 + 日期（配"各位晚上好"语音）
2. AI 大事总结（配"这是今日的AI大事"语音）
3. 逐条 AI 新闻（卡片 + 口播）
4. 逐条硬件新闻（卡片 + 口播）
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
    """获取音频时长（秒）"""
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def generate_title_html(date: str, weekday: str) -> str:
    """生成片头 HTML"""
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
body {{ margin:0; display:flex; justify-content:center; align-items:center; min-height:100vh; background:#fbf9f6; font-family:'Nunito',sans-serif; }}
.container {{ text-align:center; }}
h1 {{ font-size:120px; font-weight:700; color:#c96442; text-shadow:2px 2px 0 rgba(201,100,66,0.1); margin-bottom:40px; }}
.date {{ font-size:48px; color:#4a403a; font-weight:600; }}
</style>
</head>
<body>
<div class="container">
<h1>AI + 硬件日报</h1>
<div class="date">{date} {weekday}</div>
</div>
</body>
</html>'''


def generate_summary_html(summary: str, category: str) -> str:
    """生成总结页 HTML"""
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
body {{ margin:0; display:flex; justify-content:center; align-items:center; min-height:100vh; background:#fbf9f6; font-family:'Nunito',sans-serif; }}
.container {{ max-width:1600px; padding:80px; text-align:center; }}
h1 {{ font-size:80px; font-weight:700; color:#c96442; margin-bottom:60px; }}
.summary {{ font-size:42px; color:#4a403a; line-height:1.8; font-weight:600; }}
</style>
</head>
<body>
<div class="container">
<h1>{category}</h1>
<div class="summary">{summary}</div>
</div>
</body>
</html>'''


def generate_news_card_html(card: dict, date: str) -> str:
    """为单条新闻生成卡片 HTML（调用 LLM）"""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    prompt = f'''你是一位顶尖的前端开发 AI。根据以下新闻生成一个用于视频截图的单页 HTML。

**重要：仅输出 HTML 代码，不要任何解释文字。**

要求：
- 1920x1080 固定视图，无滚动条
- 温暖米白背景(#fbf9f6)、白色卡片、暖色点缀(#c96442)
- 居中显示：主标题"AI + 硬件日报"、日期、一张大卡片（图标+标题+详细描述150-200字）
- 使用 Nunito 字体、Material Symbols 图标、Tailwind CSS
- 数字用 <strong> 加粗，英文术语用 <code> 标注

新闻标题: {card['title']}
新闻描述: {card.get('description', '')}
分类: {card.get('category', '')}
图标: {card.get('icon', 'article')}
日期: {date}

输出完整 HTML5 文档。'''

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=6000,
    )
    
    html = response.choices[0].message.content.strip()
    if html.startswith("```"):
        html = html.split("\n", 1)[1] if "\n" in html else html
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()
    return html


def generate_tts(text: str, output_path: str, voice: str = "zh-CN-YunxiNeural"):
    """生成 TTS 音频"""
    import asyncio
    import edge_tts
    async def _gen():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    asyncio.run(_gen())


def images_to_video(image_durations: list, output_path: str):
    """将多张图片合成为视频（每张图片显示指定时长）"""
    # 创建 concat 文件
    concat_content = ""
    for img_path, duration in image_durations:
        concat_content += f"file '{img_path}'\n"
        concat_content += f"duration {duration:.2f}\n"
    # 最后一帧
    concat_content += f"file '{image_durations[-1][0]}'\n"
    
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        f.write(concat_content)
    
    # 先生成无音频视频
    temp_video = output_path + ".temp.mp4"
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', concat_file,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-r', '25',
        temp_video
    ]
    subprocess.run(cmd, capture_output=True)
    
    return temp_video, concat_file


def merge_audio(audio_paths: list, output_path: str):
    """合并多个音频文件"""
    concat_content = ""
    for i, audio_path in enumerate(audio_paths):
        concat_content += f"file '{audio_path}'\n"
        # 添加 0.5 秒静音（除了最后一个）
        if i < len(audio_paths) - 1:
            silence_path = output_path + f".silence_{i}.mp3"
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi', '-i',
                'anullsrc=r=24000:cl=mono', '-t', '0.5',
                '-q:a', '9', '-acodec', 'libmp3lame', silence_path
            ], capture_output=True)
            concat_content += f"file '{silence_path}'\n"
    
    concat_file = output_path + ".concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        f.write(concat_content)
    
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file, '-acodec', 'libmp3lame', '-b:a', '192k', output_path
    ], capture_output=True)
    
    return output_path


def generate_video(daily: dict) -> str:
    """完整视频生成流程"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    if not cards:
        raise ValueError("日报没有新闻内容")
    
    # 分类
    ai_cards = [c for c in cards if c.get('category') in ['要闻', 'AI动态', '开发生态', '行业动态', '前瞻传闻']]
    hw_cards = [c for c in cards if c.get('category') in ['芯片硬件', '量子前沿']]
    if not ai_cards:
        ai_cards = cards[:5]
    if not hw_cards:
        hw_cards = cards[5:8] if len(cards) > 5 else []
    
    output_dir = DATA_DIR / f"video_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_segments = []  # (image_path, audio_path, duration)
    
    # === 1. 片头 ===
    print("生成片头...")
    weekday_map = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
    dt = datetime.strptime(date, "%Y-%m-%d")
    weekday = weekday_map[dt.weekday()]
    date_display = f"{dt.month}月{dt.day}号"
    
    title_html = generate_title_html(date_display, f"星期{weekday}")
    title_img = str(output_dir / "00_title.png")
    render_png(title_html, title_img)
    
    title_audio = str(output_dir / "00_title.mp3")
    generate_tts(f"各位晚上好，今天是{date_display}星期{weekday}", title_audio)
    title_duration = get_audio_duration(title_audio) + 1.0
    all_segments.append((title_img, title_audio, title_duration))
    
    # === 2. AI 大事总结 ===
    print("生成 AI 总结页...")
    ai_summary = "；".join([c['title'] for c in ai_cards[:5]])
    summary_html = generate_summary_html(ai_summary, "今日 AI 大事")
    summary_img = str(output_dir / "01_ai_summary.png")
    render_png(summary_html, summary_img)
    
    summary_audio = str(output_dir / "01_ai_summary.mp3")
    generate_tts(f"这是今日的AI大事。{ai_summary}", summary_audio)
    summary_duration = get_audio_duration(summary_audio) + 0.5
    all_segments.append((summary_img, summary_audio, summary_duration))
    
    # === 3. AI 新闻逐条 ===
    for i, card in enumerate(ai_cards):
        print(f"AI 新闻 {i+1}/{len(ai_cards)}: {card['title'][:30]}...")
        html = generate_news_card_html(card, date)
        img_path = str(output_dir / f"ai_{i+1}.png")
        render_png(html, img_path)
        
        audio_path = str(output_dir / f"ai_{i+1}.mp3")
        text = f"{card['title']}。{card.get('description', '')}"
        generate_tts(text, audio_path)
        duration = get_audio_duration(audio_path) + 0.5
        all_segments.append((img_path, audio_path, duration))
    
    # === 4. 硬件过渡 ===
    if hw_cards:
        print("生成硬件总结页...")
        hw_summary = "；".join([c['title'] for c in hw_cards])
        hw_summary_html = generate_summary_html(hw_summary, "硬件前沿")
        hw_summary_img = str(output_dir / "02_hw_summary.png")
        render_png(hw_summary_html, hw_summary_img)
        
        hw_summary_audio = str(output_dir / "02_hw_summary.mp3")
        generate_tts(f"接下来是硬件领域的重要进展。{hw_summary}", hw_summary_audio)
        hw_summary_duration = get_audio_duration(hw_summary_audio) + 0.5
        all_segments.append((hw_summary_img, hw_summary_audio, hw_summary_duration))
        
        # === 5. 硬件新闻逐条 ===
        for i, card in enumerate(hw_cards):
            print(f"硬件新闻 {i+1}/{len(hw_cards)}: {card['title'][:30]}...")
            html = generate_news_card_html(card, date)
            img_path = str(output_dir / f"hw_{i+1}.png")
            render_png(html, img_path)
            
            audio_path = str(output_dir / f"hw_{i+1}.mp3")
            text = f"{card['title']}。{card.get('description', '')}"
            generate_tts(text, audio_path)
            duration = get_audio_duration(audio_path) + 0.5
            all_segments.append((img_path, audio_path, duration))
    
    # === 6. 合成视频 ===
    print(f"\n合成视频: {len(all_segments)} 个片段...")
    
    # 生成图片视频流
    image_durations = [(seg[0], seg[2]) for seg in all_segments]
    temp_video, concat_file = images_to_video(image_durations, str(output_dir / f"daily_{date}.mp4"))
    
    # 合并音频
    audio_paths = [seg[1] for seg in all_segments]
    merged_audio = str(output_dir / f"daily_{date}_audio.mp3")
    merge_audio(audio_paths, merged_audio)
    
    # 合成最终视频
    final_video = DATA_DIR / f"daily_{date}.mp4"
    cmd = [
        'ffmpeg', '-y',
        '-i', temp_video,
        '-i', merged_audio,
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        str(final_video)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg 错误: {result.stderr[:300]}")
        raise RuntimeError("视频合成失败")
    
    # 清理临时文件
    Path(temp_video).unlink(missing_ok=True)
    Path(concat_file).unlink(missing_ok=True)
    Path(merged_audio).unlink(missing_ok=True)
    
    # 清理静音文件
    for f in output_dir.glob("*.silence_*.mp3"):
        f.unlink(missing_ok=True)
    for f in output_dir.glob("*.concat.txt"):
        f.unlink(missing_ok=True)
    
    size = final_video.stat().st_size
    duration = get_audio_duration(str(final_video))
    print(f"\n视频生成完成: {final_video}")
    print(f"时长: {duration:.1f} 秒, 大小: {size / 1024 / 1024:.1f} MB")
    
    return str(final_video)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    generate_video(daily)
