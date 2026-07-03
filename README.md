# PubMed Cancer Research Daily Brief

自动检索过去 24 小时 PubMed 新发表或新收录的癌症相关高水平论文，并生成中文 Markdown 日报，重点服务肾癌/ccRCC、乳酸化、ALDOA-K230、SIRT7、UK Biobank、多组学、病理组学、影像组学、单细胞和医院队列验证方向。

## 功能

- 使用 Biopython Entrez 检索 PubMed。
- 覆盖 5 个方向：单细胞/空间组学、机制实验、乳酸化/代谢/表观遗传、病理影像 AI、UKB/MR/多组学流行病学。
- 每个方向最多筛选 3 篇论文。
- 获取 title、journal、publication date、PubMed indexed date、PMID、DOI、abstract、authors 和 PubMed link。
- 使用 `data/seen_pmids.json` 避免重复汇报。
- 支持本地 journal priority whitelist，但不编造影响因子或 CAS 分区。
- 没有 `OPENAI_API_KEY` 时仍可运行；有 key 时会增强中文摘要。
- 输出到 `reports/YYYY-MM-DD_pubmed_cancer_brief.md`。

## 本地运行

需要 Python 3.10+。推荐使用 Python 3.11 或 3.12。

```bash
cd pubmed-cancer-brief
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```dotenv
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

运行：

```bash
python main.py
```

试运行但不写入已汇报 PMID 缓存：

```bash
python main.py --dry-run
```

如果想临时忽略缓存：

```bash
python main.py --include-seen --dry-run
```

## GitHub Actions 部署

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

- `NCBI_EMAIL`：必填。
- `NCBI_API_KEY`：可选但推荐。
- `OPENAI_API_KEY`：如需 LLM 中文增强摘要则填写。
- `OPENAI_MODEL`：可选，默认 `gpt-4.1-mini`。

工作流位于 `.github/workflows/pubmed_daily.yml`，每天北京时间 03:00 自动运行。对应 UTC cron：

```yaml
cron: "0 19 * * *"
```

工作流会提交新增日报、日志和 `seen_pmids.json` 更新。

## 事实性规则

- PMID、DOI、题名、期刊、日期、作者、摘要只来自 PubMed XML。
- DOI 缺失时写 `未提供`。
- abstract 缺失时明确写 `摘要不可用，仅依据题名和 PubMed 元数据判断。`
- 不自动声称 CAS Q1 或影响因子大于 10；只有在本地白名单中才写“期刊在本地高优先级白名单中”。
- 如果某方向没有合格文献，日报会明确写文献数量不足。
