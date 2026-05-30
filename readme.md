# AI + 硬件日报

每日自动采集 AI + 硬件/半导体 + 量子计算领域新闻，经 LLM 筛选摘要后发布为 GitHub Issue。

## 对标

橘鸦 AI 早报（`imjuya/juya-ai-daily`），增加硬件/半导体板块。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 试跑（dry run，不发布）
cd scripts
python run.py

# 4. 正式发布
python run.py --publish
```

## GitHub Actions 自动化

1. Fork 本仓库
2. Settings → Secrets and variables → Actions → 添加：
   - `DEEPSEEK_API_KEY`: DeepSeek API Key
   - `DEEPSEEK_MODEL`: `deepseek-v4-flash`
   - `GITHUB_REPO`: `your-username/ai-hardware-daily`
3. 启用 Actions workflow
4. 每天北京时间早 7:00 自动运行

## 内容分类

| 分类 | 说明 |
|---|---|
| 🔥 要闻 | AI 和硬件重大事件 |
| 🤖 AI 动态 | 模型发布、产品更新 |
| 💻 开发生态 | 开源项目、工具 |
| 🔬 芯片硬件 | 制程、GPU、AI 芯片、HBM |
| ⚛️ 量子前沿 | 量子计算进展 |
| 🏭 行业动态 | 公司战略、融资 |
| 📡 前瞻传闻 | 未确认消息 |

## 过滤规则

- ✅ 保留：芯片制程、AI 芯片、量子计算、开源项目、大模型更新
- ❌ 排除：消费电子发布会、笔记本/手机/外设评测、品牌营销

## 信息源

见 `scripts/config.py` 中的 `RSS_SOURCES`，涵盖：
- 中文：量子位、机器之心、InfoQ、36kr
- 英文：SemiAnalysis、AnandTech、IEEE Spectrum、Nature Electronics 等 14 个源

## 致谢

- 橘鸦 Juya（`imjuya`）— 早报格式与卡片工具参考
- yihong0618/gitblog — Issue → Pages + RSS 转换
