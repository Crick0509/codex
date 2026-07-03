from __future__ import annotations

import logging
import re
from collections import defaultdict

from .pubmed_client import Paper


HIGH_VALUE_TERMS = {
    "renal": 5,
    "kidney": 5,
    "ccrcc": 6,
    "clear cell renal": 7,
    "lactylation": 6,
    "aldoa": 5,
    "sirt7": 5,
    "single-cell": 4,
    "spatial": 4,
    "radiomics": 4,
    "pathomics": 4,
    "radiopathomics": 5,
    "uk biobank": 5,
    "mendelian randomization": 4,
    "proteomics": 3,
    "metabolomics": 3,
    "multi-omics": 4,
}


class PaperSelector:
    def __init__(self, priority_journals: list[str]) -> None:
        self.priority_journals = {journal.lower() for journal in priority_journals}
        self.logger = logging.getLogger(__name__)

    def assign_and_select(
        self,
        papers_by_category: dict[str, dict[str, Paper]],
        categories: dict,
        seen_pmids: set[str],
    ) -> dict[str, list[Paper]]:
        selected: dict[str, list[Paper]] = {}
        globally_used: set[str] = set()
        for category_key, config in categories.items():
            candidates = []
            for paper in papers_by_category.get(category_key, {}).values():
                if paper.pmid in seen_pmids or paper.pmid in globally_used:
                    continue
                scored = self.score_paper(paper, config.get("boost_terms", []))
                scored.categories.append(category_key)
                candidates.append(scored)
            candidates.sort(key=lambda item: item.score, reverse=True)
            chosen = candidates[: int(config.get("max_papers", 3))]
            for paper in chosen:
                globally_used.add(paper.pmid)
            selected[category_key] = chosen
            self.logger.info("Selected %s papers for %s", len(chosen), category_key)
        return selected

    def score_paper(self, paper: Paper, boost_terms: list[str]) -> Paper:
        text = f"{paper.title} {paper.abstract} {paper.journal}".lower()
        score = 0.0
        if paper.journal.lower() in self.priority_journals:
            score += 12
            paper.journal_priority_note = "期刊在本地高优先级白名单中。"
        else:
            paper.journal_priority_note = "期刊分区/影响因子未自动确认，但根据期刊领域声誉纳入。"
        for term, weight in HIGH_VALUE_TERMS.items():
            if term in text:
                score += weight
        for term in boost_terms:
            term_l = term.lower()
            if term_l in text:
                score += 3
        if paper.abstract:
            score += min(5, len(paper.abstract) / 500)
        score += self._method_signal_score(text)
        paper.score = round(score, 2)
        return paper

    def _method_signal_score(self, text: str) -> float:
        patterns = [
            r"\bcohort\b",
            r"\bcrispr\b",
            r"\bxenograft\b",
            r"\borganoid\b",
            r"\bsingle[- ]cell\b",
            r"\bspatial\b",
            r"\bdeep learning\b",
            r"\bproteomic",
            r"\bmetabolomic",
            r"\bgwas\b",
        ]
        return float(sum(1 for pattern in patterns if re.search(pattern, text)))


def merge_category_results(raw: dict[str, list[str]], fetched: dict[str, Paper]) -> dict[str, dict[str, Paper]]:
    output: dict[str, dict[str, Paper]] = defaultdict(dict)
    for category, pmids in raw.items():
        for pmid in pmids:
            paper = fetched.get(pmid)
            if paper:
                output[category][pmid] = paper
    return dict(output)
