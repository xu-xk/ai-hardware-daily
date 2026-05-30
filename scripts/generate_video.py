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
from fetch_screenshots import fetch_article_screenshot
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


def make_news_card_html(card: dict, accent_color: str = '#c96442', progress_html: str = '', content_blocks: list = None, screenshot_path: str = None) -> str:
    """单条新闻卡片（带进度条 + 分块内容 + 原文截图）"""
    title = card['title']
    category = card.get('category', '')
    
    # 生成分块 HTML
    if content_blocks:
        blocks_html = ''
        for block in content_blocks:
            st = block.get('subtitle', '')
            ct = block.get('content', '')
            blocks_html += f'<div class="block"><div class="block-title">{st}</div><div class="block-content">{ct}</div></div>'
    else:
        desc = card.get('description', '')
        blocks_html = f'<div class="block"><div class="block-content">{desc}</div></div>'
    
    # 截图 HTML
    if screenshot_path and Path(screenshot_path).exists():
        # 转为 file:// URL
        img_url = 'file:///' + str(Path(screenshot_path).resolve()).replace('\\', '/')
        screenshot_html = f'<div class="screenshot"><img src="{img_url}" alt="原文截图" /></div>'
    else:
        screenshot_html = ''
    
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
.card{{width:1700px;background:#fff;border-radius:32px;border:1px solid #dad8d4;box-shadow:0 10px 30px -10px rgba(74,64,58,0.1);display:flex;overflow:hidden}}
.accent{{width:8px;background:{accent_color};flex-shrink:0}}
.main{{flex:1;display:flex;padding:32px 40px;gap:32px}}
.text-area{{flex:1;display:flex;flex-direction:column}}
.tag{{display:inline-block;background:{accent_color};color:#fff;font-size:16px;font-weight:700;padding:4px 14px;border-radius:8px;margin-bottom:14px;align-self:flex-start}}
h2{{font-size:36px;font-weight:700;color:#2d2d2d;margin:0 0 20px;line-height:1.3}}
.blocks{{display:flex;flex-direction:column;gap:12px;flex:1}}
.block{{padding:12px 16px;background:#faf9f6;border-radius:12px;border-left:4px solid {accent_color}}}
.block-title{{font-size:18px;font-weight:700;color:{accent_color};margin-bottom:4px}}
.block-content{{font-size:20px;color:#444;line-height:1.6}}
.screenshot{{width:560px;flex-shrink:0;display:flex;align-items:center;justify-content:center}}
.screenshot img{{max-width:100%;max-height:100%;border-radius:16px;border:1px solid #e8e6e2;object-fit:cover}}
</style></head><body>
<div class="page">
{progress_html}
<div class="card-area">
<div class="card"><div class="accent"></div>
<div class="main">
<div class="text-area"><div class="tag">{category}</div><h2>{title}</h2><div class="blocks">{blocks_html}</div></div>
{screenshot_html}
</div></div></div></div></body></html>'''


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
    
    # 2. 逐条新闻（LLM 扩写 + 原文截图）
    llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    screenshots_dir = DATA_DIR / f"screenshots_{date}"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    for i, card in enumerate(cards):
        color = colors[i % len(colors)]
        print(f"新闻 {i+1}/{len(cards)}: {card['title'][:25]}...")
        
        # 抓取原文截图
        screenshot_path = None
        link = card.get('link', '')
        if link:
            try:
                ss_path = str(screenshots_dir / f"news_{i+1}.png")
                fetch_article_screenshot(link, ss_path)
                if Path(ss_path).exists():
                    screenshot_path = ss_path
            except Exception as e:
                print(f"  截图失败: {e}")
        
        # LLM 生成分块内容
        short_desc = card.get('description', card['title'])
        try:
            resp = llm_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"根据以下科技新闻，生成3-4个内容块。每个块用JSON格式：{{\"subtitle\": \"小标题2-4字\", \"content\": \"内容30-50字\"}}。直接输出JSON数组，不要其他文字。\n\n主题：{card['title']}\n原始信息：{short_desc}"
                }],
                temperature=0.3,
                max_tokens=500,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1] if '\n' in raw else raw
                if raw.endswith('```'): raw = raw[:-3]
                raw = raw.strip()
            content_blocks = json.loads(raw)
            if not isinstance(content_blocks, list):
                content_blocks = [content_blocks]
        except:
            content_blocks = [{'subtitle': '详情', 'content': short_desc}]
        
        # 生成卡片（分块内容 + 截图）
        img = str(output_dir / f"news_{i+1}.png")
        render_png(make_news_card_html(card, color, progress_html, content_blocks, screenshot_path), img)
        
        # TTS 播报
        tts_parts = [f"{card['title']}。"]
        for block in content_blocks:
            tts_parts.append(block.get('content', ''))
        audio = str(output_dir / f"news_{i+1}.mp3")
        generate_tts(' '.join(tts_parts), audio)
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
