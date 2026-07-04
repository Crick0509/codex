# 在另一台电脑的 Codex 中部署 PubMed Cancer Brief

## 最简单方式：从 GitHub 获取

在另一台电脑上，让 Codex 或你自己执行：

```bash
git clone https://github.com/Crick0509/codex.git
cd codex
```

如果仓库已经存在：

```bash
git pull
```

## 本地运行

需要 Python 3.10+。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```dotenv
NCBI_EMAIL=changzh@cmu.edu.cn
NCBI_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

运行当天日报：

```bash
python main.py
```

生成指定日期日报：

```bash
python main.py --date 2026-07-03 --include-seen --dry-run
```

报告输出位置：

```text
reports/YYYY-MM-DD_pubmed_cancer_brief.md
```

## GitHub Actions 自动运行

仓库中已经包含：

```text
.github/workflows/pubmed_daily.yml
```

GitHub 已识别该 workflow，定时任务为：

```yaml
cron: "0 19 * * *"
```

对应北京时间每天 03:00。

`NCBI_EMAIL` 已写入 workflow：

```text
changzh@cmu.edu.cn
```

如果需要 LLM 增强摘要，在 GitHub 仓库中添加 Actions secrets：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`，可选，默认 `gpt-4.1-mini`
- `NCBI_API_KEY`，可选但推荐

路径：

```text
GitHub repository -> Settings -> Secrets and variables -> Actions
```

## 需要交给另一台 Codex 的文件

推荐直接给 GitHub 地址：

```text
https://github.com/Crick0509/codex.git
```

或者复制整个项目目录，但不要复制：

- `.env`
- `.venv/`
- `logs/`
- `.git/`，除非你想保留完整 git 历史

必须保留：

- `AGENTS.md`
- `README.md`
- `requirements.txt`
- `.env.example`
- `main.py`
- `config/`
- `src/`
- `data/seen_pmids.json`
- `reports/`
- `.github/workflows/pubmed_daily.yml`
- `sync_reports.ps1`

## 在另一台 Windows 电脑上同步 GitHub 日报到本地

如果希望 GitHub Actions 生成的报告每天也自动出现在本地电脑文件夹，可以让 Codex 在新电脑上创建 Windows 任务计划：

```powershell
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "你的项目路径\sync_reports.ps1"'
$Trigger = New-ScheduledTaskTrigger -Daily -At 5:00AM
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'PubMedCancerBriefLocalSync' -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Pull GitHub PubMed cancer brief reports to local folder every morning.' -Force
```

也可以手动同步：

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\sync_reports.ps1
```

## 给另一台 Codex 的一句话指令

```text
请克隆 https://github.com/Crick0509/codex.git，阅读 README.md 和 DEPLOY_TO_OTHER_CODEX.md，安装 requirements.txt，配置 .env，然后运行 python main.py 测试 PubMed Cancer Research Daily Brief 是否能生成 reports/YYYY-MM-DD_pubmed_cancer_brief.md。
```
