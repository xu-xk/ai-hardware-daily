"""
视频生成 — 图片 + 音频 → MP4（使用 FFmpeg）
"""
import json
import sys
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def generate_video(daily: dict, card_paths: list, audio_paths: list) -> str:
    """将卡片图和音频合成为视频"""
    date = daily.get("date", datetime.now().strftime("%Y-%m-%d"))
    cards = daily.get("cards", [])
    
    output_dir = DATA_DIR
    output_path = output_dir / f"daily_{date}.mp4"
    
    # 确保 card_paths 和 audio_paths 数量匹配
    min_count = min(len(card_paths), len(audio_paths))
    if min_count == 0:
        raise ValueError("没有可用的卡片图或音频")
    
    print(f"合成视频: {min_count} 个片段")
    
    # 创建 FFmpeg concat 文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        concat_file = f.name
        
        for i in range(min_count):
            # 获取音频时长
            duration = get_audio_duration(audio_paths[i])
            # 停顿 0.5 秒
            duration += 0.5
            
            f.write(f"file '{card_paths[i]}'\n")
            f.write(f"duration {duration:.2f}\n")
        
        # 最后一帧重复（避免截断）
        f.write(f"file '{card_paths[min_count-1]}'\n")
    
    # 合并所有音频为一个文件
    audio_concat = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
    audio_list = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8').name
    
    with open(audio_list, 'w') as f:
        for i in range(min_count):
            f.write(f"file '{audio_paths[i]}'\n")
            # 添加 0.5 秒静音
            silence_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi', '-i',
                'anullsrc=r=24000:cl=mono', '-t', '0.5',
                '-q:a', '9', '-acodec', 'libmp3lame', silence_path
            ], capture_output=True)
            f.write(f"file '{silence_path}'\n")
    
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', audio_list, '-acodec', 'copy', audio_concat
    ], capture_output=True)
    
    # 合成视频
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', concat_file,
        '-i', audio_concat,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
        str(output_path)
    ]
    
    print(f"执行 FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg 错误: {result.stderr[:500]}")
        raise RuntimeError("FFmpeg 合成失败")
    
    # 清理临时文件
    Path(concat_file).unlink(missing_ok=True)
    Path(audio_concat).unlink(missing_ok=True)
    Path(audio_list).unlink(missing_ok=True)
    
    file_size = output_path.stat().st_size
    print(f"视频已生成: {output_path} ({file_size / 1024 / 1024:.1f} MB)")
    
    return str(output_path)


if __name__ == "__main__":
    date = datetime.now().strftime("%Y-%m-%d")
    daily_file = DATA_DIR / f"daily_{date}.json"
    
    if not daily_file.exists():
        print(f"未找到日报数据: {daily_file}")
        sys.exit(1)
    
    daily = json.loads(daily_file.read_text(encoding="utf-8"))
    
    # 查找卡片图和音频
    cards_dir = DATA_DIR / f"cards_{date}"
    audio_dir = DATA_DIR / f"audio_{date}"
    
    if not cards_dir.exists() or not audio_dir.exists():
        print("请先生成卡片图和音频")
        sys.exit(1)
    
    card_paths = sorted([str(p) for p in cards_dir.glob("news_*.png")])
    audio_paths = sorted([str(p) for p in audio_dir.glob("news_*.mp3")])
    
    print(f"找到 {len(card_paths)} 张卡片图, {len(audio_paths)} 个音频")
    generate_video(daily, card_paths, audio_paths)
