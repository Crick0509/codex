from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .pubmed_client import Paper
from .summarizer import Summarizer


class ReportWriter:
    def __init__(self, reports_dir: Path, summarizer: Summarizer) -> None:
        self.reports_dir = reports_dir
        self.summarizer = summarizer
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        selected: dict[str, list[Paper]],
        categories: dict,
        run_time: datetime,
    ) -> Path:
        report_date = run_time.strftime("%Y-%m-%d")
        path = self.reports_dir / f"{report_date}_pubmed_cancer_brief.md"
        lines: list[str] = []
        lines.extend(
            [
                "# PubMed Cancer Research Daily Brief",
                "",
                f"日期：{report_date}",
                f"检索时间：北京时间 {run_time.strftime('%H:%M')}",
                "检索范围：过去 24 小时 PubMed 新发表或新收录文献",
                "",
                "## 1. 今日最值得关注的热点",
                "",
            ]
        )
        lines.extend(self._hotspots(selected, categories))
        lines.extend(["", "## 2. 按方向汇报文献", ""])
        summaries_by_pmid: dict[str, dict[str, str]] = {}
        for category_key, config in categories.items():
            label = config["label"]
            papers = selected.get(category_key, [])
            lines.extend([f"### {label}", ""])
            if not papers:
                lines.extend(["过去 24 小时该方向符合条件且未曾汇报的文献数量不足。", ""])
                continue
            for index, paper in enumerate(papers, start=1):
                summary = self.summarizer.summarize_paper(paper, label)
                summaries_by_pmid[paper.pmid] = summary
                lines.extend(self._paper_block(index, paper, summary))
        lines.extend(self._transferable_methods(summaries_by_pmid))
        lines.extend(self._specific_inspiration())
        lines.extend(self._followups())
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path

    def _hotspots(self, selected: dict[str, list[Paper]], categories: dict) -> list[str]:
        hotspots = []
        for category_key, papers in selected.items():
            if papers:
                label = categories[category_key]["label"].split("：", 1)[-1]
                titles = "；".join(paper.title for paper in papers[:2])
                hotspots.append(f"- {label}：今日检索到可关注文献，代表题名包括 {titles}。可为 ccRCC 的机制假设、队列分析或验证体系提供借鉴。")
        if not hotspots:
            return ["过去 24 小时未筛选到符合条件且未曾汇报的高优先级文献；建议明日继续追踪并适当放宽关键词。"]
        return hotspots[:5]

    def _paper_block(self, index: int, paper: Paper, summary: dict[str, str]) -> list[str]:
        abstract_note = "是" if paper.abstract_missing else "否"
        authors = ", ".join(paper.authors[:8]) + (" et al." if len(paper.authors) > 8 else "")
        return [
            f"#### Paper {index}",
            f"Title: {paper.title or '未提供'}",
            f"Journal: {paper.journal or '未提供'}",
            f"Journal priority note: {paper.journal_priority_note}",
            f"Date: Publication date: {paper.publication_date or '未提供'}; PubMed indexed date: {paper.indexed_date or '未提供'}",
            f"PMID: {paper.pmid}",
            f"DOI: {paper.doi or '未提供'}",
            f"Authors: {authors or '未提供'}",
            f"Abstract unavailable: {abstract_note}",
            f"Study type: {summary['study_type']}",
            f"Core methods: {summary['core_methods']}",
            f"Main findings: {summary['main_findings']}",
            f"Innovation: {summary['innovation']}",
            f"Relevance to ccRCC: {summary['relevance_to_ccrcc']}",
            f"Actionable idea: {summary['actionable_idea']}",
            f"PubMed link: {paper.pubmed_link}",
            "",
        ]

    def _transferable_methods(self, summaries_by_pmid: dict[str, dict[str, str]]) -> list[str]:
        lines = ["## 3. 今日可迁移到肾癌研究的创新方法", ""]
        methods = [summary["core_methods"] for summary in summaries_by_pmid.values() if summary.get("core_methods")]
        if not methods:
            lines.append("今日未筛选到足够文献提取稳定可迁移方法。")
        else:
            for method in methods[:8]:
                lines.append(f"- {method}")
        lines.append("")
        return lines

    def _specific_inspiration(self) -> list[str]:
        return [
            "## 4. 对用户当前课题的具体启发",
            "",
            "- ccRCC 风险预测：优先记录可迁移的暴露定义、结局窗口、验证策略和校准/决策曲线分析。",
            "- 乳酸化与 ALDOA-K230：追踪乳酸代谢、Kla、糖酵解和蛋白翻译后修饰文献，建立 TCGA/CPTAC 到湿实验的证据链。",
            "- SIRT7 介导调控：关注去乙酰化/去乳酸化、核糖体生物发生、代谢重编程和免疫微环境之间的连接。",
            "- UKB 蛋白组/代谢组：将候选蛋白、代谢物和暴露映射到 UKB/Olink/Nightingale 字段，设计发现-验证-因果推断框架。",
            "- 微塑料、超加工食品、包装相关暴露、EDCs 与噪声：将环境暴露文献转化为 UKB 暴露变量、替代指标或 MR 工具变量清单。",
            "- 数字病理与影像组学：把模型输入、特征融合、外部验证和可解释性图形迁移到医院 CT/MRI/WSI 队列。",
            "- 单细胞和空间验证：将候选通路定位到细胞类型、空间邻域、免疫浸润和代谢生态位。",
            "- 医院队列验证：为每篇可迁移论文记录需要补充的临床变量、样本类型、实验材料和伦理数据条件。",
            "",
        ]

    def _followups(self) -> list[str]:
        return [
            "## 5. 明日或后续可执行任务",
            "",
            "- PubMed 持续追踪关键词：ccRCC lactylation、renal cell carcinoma spatial transcriptomics、kidney cancer radiopathomics。",
            "- Python/R 分析：建立 PMID-关键词-方向-候选课题的 CSV 索引，累计 30 天后做热点词共现网络。",
            "- UKB 检查：整理肾癌 ICD-10/ICD-O 结局、Olink 蛋白、Nightingale 代谢物、饮食和环境暴露变量。",
            "- TCGA/CPTAC 验证：检验 ALDOA、SIRT7、LDHA、SLC16A1/MCT1、SLC16A3/MCT4 与预后、免疫浸润和代谢通路的关系。",
            "- scRNA-seq 验证：在公开 ccRCC 单细胞数据中定位 ALDOA/SIRT7 高表达细胞群及其乳酸代谢邻近信号。",
            "- 空间转录组：设计肿瘤-免疫-血管空间邻域图，验证糖酵解/乳酸通路的区域富集。",
            "- 医院队列实验：为候选机制准备 IHC/IF、Western blot、qPCR、乳酸检测、Kla 抗体检测和功能实验清单。",
            "- 图形想法：制作“暴露-多组学-影像病理-机制验证-外部队列”的 ccRCC 转化研究路线图。",
            "- 论文/基金想法：以环境暴露和代谢重编程为入口，串联 UKB 发现、MR 因果推断、CPTAC 验证和医院队列实验。",
            "",
        ]
