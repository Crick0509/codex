from __future__ import annotations

import json
import logging
import os
from typing import Any

from .pubmed_client import Paper


class Summarizer:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.logger = logging.getLogger(__name__)

    def summarize_paper(self, paper: Paper, category_label: str) -> dict[str, str]:
        if self.api_key:
            try:
                return self._summarize_with_openai(paper, category_label)
            except Exception as exc:
                self.logger.warning("OpenAI summarization failed for PMID %s: %s", paper.pmid, exc)
        return self._summarize_locally(paper, category_label)

    def _summarize_with_openai(self, paper: Paper, category_label: str) -> dict[str, str]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        prompt = {
            "category": category_label,
            "title": paper.title,
            "journal": paper.journal,
            "pmid": paper.pmid,
            "doi": paper.doi,
            "abstract": paper.abstract or "ABSTRACT_UNAVAILABLE",
            "instruction": (
                "Return concise Chinese JSON with keys study_type, core_methods, main_findings, "
                "innovation, relevance_to_ccrcc, actionable_idea. Do not invent metadata. "
                "If abstract is unavailable, say 摘要不可用，仅依据题名和期刊元数据判断."
            ),
        }
        response = client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You summarize PubMed cancer papers in Chinese with strict factual caution."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return self._normalize_summary(parsed, paper)

    def _summarize_locally(self, paper: Paper, category_label: str) -> dict[str, str]:
        text = f"{paper.title}. {paper.abstract}".lower()
        methods = []
        method_terms = {
            "single-cell/spatial profiling": ["single-cell", "single cell", "scrna", "spatial"],
            "functional/mechanistic validation": ["knockout", "knockdown", "crispr", "xenograft", "organoid", "mouse"],
            "multi-omics or molecular association analysis": ["proteomic", "metabolomic", "gwas", "multi-omics", "eqtl", "pqtl"],
            "AI/pathology/imaging modeling": ["deep learning", "machine learning", "radiomics", "pathology", "whole-slide"],
            "metabolism/epigenetic analysis": ["lactate", "glycolysis", "lactylation", "epigenetic", "post-translational"],
        }
        for label, terms in method_terms.items():
            if any(term in text for term in terms):
                methods.append(label)
        first_sentence = self._first_sentence(paper.abstract) if paper.abstract else "摘要不可用，仅依据题名和 PubMed 元数据判断。"
        return self._normalize_summary(
            {
                "study_type": self._infer_study_type(text, category_label),
                "core_methods": "；".join(methods) if methods else "PubMed 摘要中未能自动识别明确方法；需阅读全文确认。",
                "main_findings": first_sentence,
                "innovation": "可关注其研究设计、数据类型或验证链条是否能迁移到 ccRCC；具体创新点需结合全文确认。",
                "relevance_to_ccrcc": self._relevance(text),
                "actionable_idea": self._actionable_idea(text),
            },
            paper,
        )

    def _normalize_summary(self, data: dict[str, Any], paper: Paper) -> dict[str, str]:
        defaults = {
            "study_type": "未自动确认",
            "core_methods": "未自动确认",
            "main_findings": "摘要不可用，仅依据题名和 PubMed 元数据判断。" if paper.abstract_missing else "未自动确认",
            "innovation": "未自动确认",
            "relevance_to_ccrcc": "可作为肾癌/ccRCC 研究的问题、方法或验证思路参考；需阅读全文后决定是否纳入。",
            "actionable_idea": "阅读全文，提取可复用变量、模型、实验体系或验证数据集。",
        }
        normalized = {}
        for key, default in defaults.items():
            value = str(data.get(key, "")).strip()
            normalized[key] = value or default
        return normalized

    def _infer_study_type(self, text: str, category_label: str) -> str:
        if "mendelian randomization" in text:
            return "孟德尔随机化/遗传流行病学研究"
        if "cohort" in text or "uk biobank" in text:
            return "人群队列或数据库挖掘研究"
        if "xenograft" in text or "organoid" in text or "crispr" in text:
            return "机制实验与功能验证研究"
        if "deep learning" in text or "radiomics" in text:
            return "AI 建模、影像组学或病理组学研究"
        if "single-cell" in text or "spatial" in text:
            return "单细胞/空间组学研究"
        return category_label.replace("方向", "主题")

    def _first_sentence(self, abstract: str) -> str:
        for separator in (". ", "。"):
            if separator in abstract:
                return abstract.split(separator)[0].strip() + ("。" if separator == "。" else ".")
        return abstract[:450] + ("..." if len(abstract) > 450 else "")

    def _relevance(self, text: str) -> str:
        if any(term in text for term in ("renal", "kidney", "ccrcc", "clear cell renal")):
            return "与肾癌/ccRCC 直接相关，可优先评估其终点、分层、分子机制或验证体系。"
        if any(term in text for term in ("lactylation", "lactate", "glycolysis", "aldoa", "sirt7")):
            return "可迁移到乳酸代谢、ALDOA-K230 乳酸化或 SIRT7 调控轴的机制假设。"
        if any(term in text for term in ("radiomics", "pathology", "deep learning", "multi-omics")):
            return "可为 ccRCC 影像/病理/组学融合建模提供方法参照。"
        return "虽非肾癌特异，但可能提供癌症机制、数据挖掘或转化验证思路。"

    def _actionable_idea(self, text: str) -> str:
        if "uk biobank" in text or "cohort" in text:
            return "检查 UKB 暴露、蛋白/代谢组、癌症登记和死亡结局变量，设计 ccRCC 风险预测或外部验证分析。"
        if "single-cell" in text or "spatial" in text:
            return "在 ccRCC scRNA-seq/空间数据中复现关键细胞群、配体受体或空间邻域信号。"
        if "radiomics" in text or "pathology" in text:
            return "将其特征工程或模型验证框架迁移到医院队列 CT/MRI/WSI 与转录组联合分析。"
        if "lactate" in text or "glycolysis" in text or "lactylation" in text:
            return "围绕 ALDOA/SIRT7/LDHA/MCT 轴设计 TCGA-CPTAC 验证、敲降/过表达和乳酸化检测。"
        return "阅读全文后提取可复用关键词、数据集、实验模型和图形组织方式。"
