"""
AI + 硬件日报 — 配置文件
"""
import os
from pathlib import Path

# === 项目路径 ===
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"

# === DeepSeek API ===
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

# === GitHub ===
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("REPO_NAME", "")  # 格式: owner/repo

# === RSS 源配置 ===
RSS_SOURCES = {
    # ─── AI ───
    "ai": [
        {
            "name": "量子位",
            "url": "https://www.qbitai.com/feed",
            "lang": "zh",
            "category": "ai",
            "weight": 3,  # 优先级权重
        },
        {
            "name": "机器之心",
            "url": "https://www.jiqizhixin.com/rss",
            "lang": "zh",
            "category": "ai",
            "weight": 3,
        },
        {
            "name": "InfoQ",
            "url": "https://www.infoq.cn/feed",
            "lang": "zh",
            "category": "dev",
            "weight": 2,
        },
        {
            "name": "36kr",
            "url": "https://36kr.com/feed",
            "lang": "zh",
            "category": "industry",
            "weight": 2,
        },
        {
            "name": "Google AI Blog",
            "url": "https://blog.google/technology/ai/rss/",
            "lang": "en",
            "category": "ai",
            "weight": 3,
        },
        {
            "name": "The Verge AI",
            "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "lang": "en",
            "category": "ai",
            "weight": 2,
        },
        {
            "name": "TechCrunch AI",
            "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "lang": "en",
            "category": "ai",
            "weight": 2,
        },
        {
            "name": "MIT Tech Review",
            "url": "https://www.technologyreview.com/feed/",
            "lang": "en",
            "category": "ai",
            "weight": 2,
        },
        {
            "name": "Ars Technica",
            "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "lang": "en",
            "category": "tech",
            "weight": 1,
        },
    ],
    # ─── 硬件 / 半导体 ───
    "hardware": [
        {
            "name": "SemiAnalysis",
            "url": "https://semianalysis.com/feed/",
            "lang": "en",
            "category": "semiconductor",
            "weight": 3,
        },
        {
            "name": "Chips and Cheese",
            "url": "https://chipsandcheese.com/feed/",
            "lang": "en",
            "category": "chip_arch",
            "weight": 3,
        },
        {
            "name": "AnandTech",
            "url": "https://www.anandtech.com/rss/",
            "lang": "en",
            "category": "hardware",
            "weight": 3,
        },
        {
            "name": "ServeTheHome",
            "url": "https://www.servethehome.com/feed/",
            "lang": "en",
            "category": "server",
            "weight": 2,
        },
        {
            "name": "EETimes",
            "url": "https://www.eetimes.com/feed/",
            "lang": "en",
            "category": "ee",
            "weight": 2,
        },
        {
            "name": "IEEE Spectrum",
            "url": "https://spectrum.ieee.org/feeds/feed.rss",
            "lang": "en",
            "category": "research",
            "weight": 2,
        },
        {
            "name": "Nature Electronics",
            "url": "https://www.nature.com/natelectron.rss",
            "lang": "en",
            "category": "research",
            "weight": 3,
        },
        {
            "name": "The Register",
            "url": "https://www.theregister.com/headlines.atom",
            "lang": "en",
            "category": "industry",
            "weight": 1,
        },
        {
            "name": "The Register (Data Center)",
            "url": "https://www.theregister.com/data_centre/headlines.atom",
            "lang": "en",
            "category": "datacenter",
            "weight": 2,
        },
        {
            "name": "NextPlatform",
            "url": "https://www.nextplatform.com/feed/",
            "lang": "en",
            "category": "hpc",
            "weight": 2,
        },
        {
            "name": "SemiWiki",
            "url": "https://semiwiki.com/feed/",
            "lang": "en",
            "category": "eda",
            "weight": 2,
        },
        {
            "name": "Tom's Hardware",
            "url": "https://www.tomshardware.com/feeds/all",
            "lang": "en",
            "category": "hardware",
            "weight": 1,  # 需过滤消费电子
        },
    ],
    # ─── 量子计算 ───
    "quantum": [
        {
            "name": "Quantum Computing Report",
            "url": "https://quantumcomputingreport.com/feed/",
            "lang": "en",
            "category": "quantum",
            "weight": 2,
        },
    ],
}

# ─── 过滤关键词（排除消费电子水文）───
EXCLUDE_KEYWORDS = [
    "笔记本", "laptop", "notebook", "平板", "tablet",
    "手机", "smartphone", "iPhone", "Galaxy S", "Pixel",
    "耳机", "earbuds", "AirPods", "音箱", "speaker",
    "显示器", "monitor", "键盘", "keyboard", "鼠标", "mouse",
    "开箱", "评测", "unboxing", "review",
    "游戏本", "gaming laptop", "机械键盘",
]

# ─── 硬件保留关键词（优先保留）───
HARDWARE_KEEP_KEYWORDS = [
    "芯片", "chip", "semiconductor", "制程", "process node",
    "GPU", "AI 芯片", "AI chip", "NPU", "TPU",
    "HBM", "CoWoS", "先进封装", "advanced packaging",
    "光刻", "lithography", "EUV", "ASML",
    "量子", "quantum", "qubit",
    "RISC-V", "Chiplet", "UCIe",
    "台积电", "TSMC", "三星半导体", "Intel Foundry",
    "寒武纪", "海光", "摩尔线程", "壁仞", "沐曦",
    "数据中心", "data center", "服务器", "server",
    "算力", "computing power", "FLOPS",
    "存储", "memory", "DRAM", "NAND", "CXL",
    "北方华创", "中微", "拓荆",
]

# ─── LLM Prompt 模板 ───
SYSTEM_PROMPT = """你是一位专业的 AI + 硬件科技日报编辑。你的任务是将多条原始新闻筛选、分类、摘要，生成一份结构化的每日日报。

## 分类体系
1. 🔥 要闻 — AI 和硬件领域的重大事件（1-3 条）
2. 🤖 AI 动态 — 模型发布、产品更新、能力突破
3. 💻 开发生态 — 开源项目、工具、框架、CLI
4. 🔬 芯片硬件 — 制程、GPU、AI 芯片、HBM、先进封装、数据中心硬件
5. ⚛️ 量子前沿 — 量子计算进展
6. 🏭 行业动态 — 公司战略、融资、政策、人事变动
7. 📡 前瞻传闻 — 未确认消息、分析师预测

## 过滤规则（严格执行）
**排除以下内容**：
- 消费电子发布会（品牌发新笔记本/手机/平板/外设/耳机）
- 产品开箱评测
- 品牌营销活动
- 与 AI/硬件技术无关的八卦

**保留以下内容**：
- 芯片架构/制程进展
- 数据中心硬件（GPU 服务器、AI 加速卡）
- 半导体设备/材料突破
- 量子计算里程碑
- RISC-V / Chiplet / 先进封装
- 国产算力芯片进展
- 大模型发布/更新
- 重要开源项目

## 输出要求
为每条新闻生成：
- **标题**：简洁有力，15-30 字
- **摘要**：信息密度高，30-60 字，包含关键数据
- **分类**：上述 7 类之一
- **重要度**：1-5 星
- **来源**：原始来源名称

最终输出 JSON 格式：
```json
{
  "date": "2026-05-31",
  "mainTitle": "AI + 硬件日报",
  "summary": "今日要点一句话概括",
  "cards": [
    {
      "title": "标题",
      "description": "摘要内容",
      "category": "要闻",
      "importance": 5,
      "source": "来源名",
      "icon": "trending_up"
    }
  ]
}
```

## 注意事项
- 每日精选 8-15 条，宁缺毋滥
- 同一事件不同源只保留一条，选信息最全的
- 英文新闻的摘要用中文写
- 数字、型号、技术术语保留原文
- icon 从 Google Material Symbols 中选择 snake_case 名称
"""

USER_PROMPT_TEMPLATE = """以下是今日采集到的原始新闻（共 {count} 条），请筛选、分类、摘要，生成今日日报。

{news_text}

请严格按照 JSON 格式输出，不要包含其他文字。"""
