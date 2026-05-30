"""
视频生成 v4 — 最终版
结构：
1. 片头："AI 早报"超大字
2. 资讯概览页（2×2 卡片网格）
3. 逐条新闻（左侧色条卡片）
"""
import json, sys, subprocess, os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from generate_card import render_png
from openai import OpenAI


def get_audio_duration(audio_path: str) -> float:
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    return float(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())


def generate_tts(text: str, output_path: str, voice: str = "zh-CN-YunxiNeural"):
    import asyncio, edge_tts
    async def _gen():
        await edge_tts.Communicate(text, voice).save(output_path)
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


def make_overview_html(daily: dict, date_str: str) -> str:
    """生成资讯概览页"""
    cards = daily.get('cards', [])
    
    # 按分类分组
    categories = {}
    for c in cards:
        cat = c.get('category', '其他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(c)
    
    # 分类配置
    cat_config = {
        '要闻': {'color': 'c-orange', 'icon': '★', 'items': []},
        'AI动态': {'color': 'c-orange', 'icon': '★', 'items': []},
        '开发生态': {'color': 'c-yellow', 'icon': '</>', 'items': []},
        '产品应用': {'color': 'c-blue', 'icon': '▦', 'items': []},
        '行业动态': {'color': 'c-red', 'icon': '◎', 'items': []},
        '前瞻传闻': {'color': 'c-orange', 'icon': '⚠', 'items': []},
        '芯片硬件': {'color': 'c-red', 'icon': '◎', 'items': []},
        '量子前沿': {'color': 'c-blue', 'icon': '▦', 'items': []},
    }
    
    for cat, items in categories.items():
        if cat in cat_config:
            cat_config[cat]['items'] = items
    
    # 生成卡片 HTML
    cards_html = ''
    for cat_name, cfg in cat_config.items():
        if not cfg['items']:
            continue
        li_html = ''.join([f'<li>{c["title"][:25]}</li>' for c in cfg['items'][:3]])
        cards_html += f'''
    <div class="card {cfg['color']}">
      <div class="card-header"><span class="card-icon">{cfg['icon']}</span><span class="card-title">{cat_name}</span></div>
      <ul class="card-list">{li_html}</ul>
    </div>'''
    
    # 底部标签
    tags = [c['title'][:6] for c in cards[:6]]
    tags_html = ''.join([f'<span class="tag">{t}</span>' for t in tags])
    
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans SC',sans-serif;background:#fbf9f6;color:#333;min-height:100vh;display:flex;justify-content:center;align-items:center}}
.page{{width:1920px;height:1080px;padding:40px 60px;display:flex;flex-direction:column}}
.nav{{display:flex;gap:0;margin-bottom:32px}}
.nav-item{{padding:10px 28px;font-size:20px;font-weight:600;border-radius:10px 10px 0 0}}
.nav-item.active{{background:#c96442;color:#fff}}
.nav-item:not(.active){{background:#fff;color:#666;border:1px solid #e5e5e5;border-bottom:none}}
.title{{font-size:52px;font-weight:700;color:#c96442;text-align:center;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;flex:1}}
.card{{background:#fff;border-radius:20px;padding:24px 28px;border:1px solid #e8e6e2;box-shadow:0 4px 16px -4px rgba(74,64,58,0.06)}}
.card-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
.card-icon{{font-size:28px;font-weight:700}}
.card-title{{font-size:22px;font-weight:700}}
.card-list{{list-style:none;padding:0}}
.card-list li{{font-size:17px;line-height:1.7;color:#555;padding:3px 0;padding-left:16px;position:relative}}
.card-list li::before{{content:'';position:absolute;left:0;top:11px;width:8px;height:8px;border-radius:50%}}
.c-orange .card-icon,.c-orange .card-title{{color:#c96442}}.c-orange .card-list li::before{{background:#c96442}}
.c-yellow .card-icon,.c-yellow .card-title{{color:#e09f3e}}.c-yellow .card-list li::before{{background:#e09f3e}}
.c-blue .card-icon,.c-blue .card-title{{color:#335c67}}.c-blue .card-list li::before{{background:#335c67}}
.c-red .card-icon,.c-red .card-title{{color:#9e2a2b}}.c-red .card-list li::before{{background:#9e2a2b}}
.footer-bar{{margin-top:auto;text-align:center;padding:14px;background:rgba(45,45,45,0.85);border-radius:14px;color:#fff;font-size:18px;font-weight:600;letter-spacing:2px}}
.tags{{display:flex;justify-content:center;gap:12px;margin-top:14px;flex-wrap:wrap}}
.tag{{background:#f0efeb;padding:6px 16px;border-radius:8px;font-size:14px;color:#888;font-weight:600}}
</style></head><body>
<div class="page">
  <div class="nav">
    <div class="nav-item active">Intro</div>
    <div class="nav-item">要闻</div><div class="nav-item">开发生态</div>
    <div class="nav-item">产品应用</div><div class="nav-item">行业动态</div><div class="nav-item">前瞻与传闻</div>
  </div>
  <div class="title">{date_str} 资讯概览</div>
  <div class="grid">{cards_html}</div>
  <div class="footer-bar">今天是 {date_str}</div>
  <div class="tags">{tags_html}</div>
</div>
</body></html>'''


def make_news_card_html(card: dict, accent_color: str = '#c96442', progress_html: str = '', bullet_points: list = None) -> str:
    """单条新闻卡片（带进度条 + 要点列表）"""
    title = card['title']
    category = card.get('category', '')
    
    # 生成要点列表 HTML
    if bullet_points:
        items_html = ''.join([f'<li>{bp}</li>' for bp in bullet_points])
        list_html = f'<ul class="points">{items_html}</ul>'
    else:
        desc = card.get('description', '')
        list_html = f'<div class="desc">{desc}</div>'
    
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;600;700&display=swap" rel="stylesheet" />
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fbf9f6;font-family:'Noto Sans SC',sans-serif}}
.page{{width:1920px;height:1080px;display:flex;flex-direction:column}}
.progress{{display:flex;height:8px;width:100%}}
.progress .seg{{height:100%}}
.card-area{{flex:1;display:flex;justify-content:center;align-items:center;padding:40px}}
.card{{width:1600px;background:#fff;border-radius:32px;border:1px solid #dad8d4;box-shadow:0 10px 30px -10px rgba(74,64,58,0.1);display:flex;overflow:hidden}}
.accent{{width:8px;background:{accent_color};flex-shrink:0}}
.content{{flex:1;padding:60px 80px}}
.tag{{display:inline-block;background:{accent_color};color:#fff;font-size:20px;font-weight:700;padding:6px 20px;border-radius:8px;margin-bottom:24px}}
h2{{font-size:48px;font-weight:700;color:#2d2d2d;margin:0 0 32px;line-height:1.3}}
.points{{list-style:none;padding:0;margin:0}}
.points li{{font-size:28px;color:#444;line-height:1.6;padding:10px 0 10px 28px;position:relative;border-bottom:1px solid #f0efeb}}
.points li:last-child{{border-bottom:none}}
.points li::before{{content:'';position:absolute;left:0;top:18px;width:10px;height:10px;border-radius:50%;background:{accent_color}}}
.desc{{font-size:28px;color:#666;line-height:1.6}}
</style></head><body>
<div class="page">
{progress_html}
<div class="card-area">
<div class="card"><div class="accent"></div>
<div class="content"><div class="tag">{category}</div><h2>{title}</h2>{list_html}</div>
</div></div></div></body></html>'''


def images_to_video(image_durations, output_path):
    concat = ""
    for img, dur in image_durations:
        concat += f"file '{img}'\nduration {dur:.2f}\n"
    concat += f"file '{image_durations[-1][0]}'\n"
    cf = output_path + ".concat.txt"
    with open(cf, 'w', encoding='utf-8') as f: f.write(concat)
    tv = output_path + ".temp.mp4"
    subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',cf,'-c:v','libx264','-pix_fmt','yuv420p','-r','25',tv], capture_output=True)
    return tv, cf


def merge_audio(audio_paths, output_path):
    concat = ""
    silences = []
    for i, ap in enumerate(audio_paths):
        concat += f"file '{ap}'\n"
        if i < len(audio_paths) - 1:
            sp = output_path + f".s{i}.mp3"
            subprocess.run(['ffmpeg','-y','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','0.5','-q:a','9','-acodec','libmp3lame',sp], capture_output=True)
            concat += f"file '{sp}'\n"
            silences.append(sp)
    cf = output_path + ".concat.txt"
    with open(cf, 'w', encoding='utf-8') as f: f.write(concat)
    subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',cf,'-acodec','libmp3lame','-b:a','192k',output_path], capture_output=True)
    for s in silences: Path(s).unlink(missing_ok=True)
    Path(cf).unlink(missing_ok=True)


def generate_video(daily: dict) -> str:
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    if not cards: raise ValueError("没有新闻")
    
    output_dir = DATA_DIR / f"video_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    segments = []
    weekday_map = {0:'一',1:'二',2:'三',3:'四',4:'五',5:'六',6:'日'}
    dt = datetime.strptime(date, "%Y-%m-%d")
    weekday = weekday_map[dt.weekday()]
    date_display = f"{dt.month}月{dt.day}号"
    
    colors = ['#c96442', '#e09f3e', '#335c67', '#9e2a2b']
    
    # 1. 资讯概览（直接当片头）
    print("概览页（片头）...")
    img = str(output_dir / "01_overview.png")
    render_png(make_overview_html(daily, date), img)
    audio = str(output_dir / "01_overview.mp3")
    generate_tts(f"各位晚上好，今天是{date_display}星期{weekday}，以下是今天的主要内容。", audio)
    segments.append((img, audio, get_audio_duration(audio) + 1.5))
    
    # 进度条 HTML
    progress_html = '<div class="progress">' + ''.join(['<div class="seg" style="flex:1"></div>' for _ in range(len(cards))]) + '</div>'
    
    # 2. 逐条新闻（LLM 扩写描述）
    llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    for i, card in enumerate(cards):
        color = colors[i % len(colors)]
        print(f"新闻 {i+1}/{len(cards)}: {card['title'][:25]}...")
        
        # LLM 提炼要点
        short_desc = card.get('description', card['title'])
        try:
            resp = llm_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"根据以下科技新闻，提炼3-5个关键要点，每个要点一句话（15-25字），用中文。直接输出要点，每行一个，不要编号不要标题。\n\n主题：{card['title']}\n原始信息：{short_desc}"
                }],
                temperature=0.3,
                max_tokens=300,
            )
            bullet_points = [p.strip().lstrip('0123456789.、-•· ') for p in resp.choices[0].message.content.strip().split('\n') if p.strip()]
            bullet_points = [p for p in bullet_points if len(p) > 4][:5]
        except:
            bullet_points = [short_desc]
        
        # 生成卡片（要点列表）
        img = str(output_dir / f"news_{i+1}.png")
        render_png(make_news_card_html(card, color, progress_html, bullet_points), img)
        
        # TTS 播报（念标题 + 要点）
        tts_text = f"{card['title']}。" + '。'.join(bullet_points)
        audio = str(output_dir / f"news_{i+1}.mp3")
        generate_tts(tts_text, audio)
        segments.append((img, audio, get_audio_duration(audio) + 0.5))
    
    # 合成
    print(f"\n合成: {len(segments)} 片段...")
    ids = [(s[0], s[2]) for s in segments]
    tv, cf = images_to_video(ids, str(output_dir / f"daily_{date}.mp4"))
    ma = str(output_dir / f"daily_{date}_audio.mp3")
    merge_audio([s[1] for s in segments], ma)
    
    final = DATA_DIR / f"daily_{date}.mp4"
    r = subprocess.run(['ffmpeg','-y','-i',tv,'-i',ma,'-c:v','copy','-c:a','aac','-b:a','192k','-shortest',str(final)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error: {r.stderr[:300]}")
        raise RuntimeError("合成失败")
    
    Path(tv).unlink(missing_ok=True)
    Path(cf).unlink(missing_ok=True)
    Path(ma).unlink(missing_ok=True)
    
    dur = get_audio_duration(str(final))
    sz = final.stat().st_size
    print(f"完成: {final} | {dur:.1f}s | {sz/1024/1024:.1f}MB")
    return str(final)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily = json.loads(open(DATA_DIR / f"daily_{date}.json", encoding="utf-8").read())
    generate_video(daily)
