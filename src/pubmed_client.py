from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError

from Bio import Entrez

from .utils import clean_text


@dataclass
class Paper:
    pmid: str
    title: str = ""
    journal: str = ""
    publication_date: str = ""
    indexed_date: str = ""
    doi: str = ""
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    pubmed_link: str = ""
    categories: list[str] = field(default_factory=list)
    score: float = 0.0
    journal_priority_note: str = ""
    abstract_missing: bool = False


class PubMedClient:
    def __init__(self, email: str, api_key: str | None = None, tool: str = "pubmed-cancer-brief") -> None:
        Entrez.email = email
        Entrez.tool = tool
        if api_key:
            Entrez.api_key = api_key
        self.delay_seconds = 0.11 if api_key else 0.34
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_env(cls) -> "PubMedClient":
        email = os.getenv("NCBI_EMAIL", "").strip()
        if not email:
            raise RuntimeError("NCBI_EMAIL is required by NCBI Entrez.")
        return cls(email=email, api_key=os.getenv("NCBI_API_KEY", "").strip() or None)

    def _read_with_retries(self, call, *args, **kwargs) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                time.sleep(self.delay_seconds)
                handle = call(*args, **kwargs)
                try:
                    return Entrez.read(handle)
                finally:
                    handle.close()
            except (HTTPError, URLError, RuntimeError) as exc:
                last_error = exc
                wait = attempt * 2
                self.logger.warning("Entrez request failed on attempt %s: %s; retrying in %ss", attempt, exc, wait)
                time.sleep(wait)
        raise RuntimeError(f"Entrez request failed after retries: {last_error}")

    def search_recent_pmids(
        self,
        query: str,
        hours: int = 24,
        retmax: int = 100,
        target_date: date | None = None,
    ) -> list[str]:
        # PubMed supports relative date searches by day. Combining EDAT and PDAT catches
        # newly indexed records and newly published records without fabricating timestamps.
        term = f"({query})"
        found: list[str] = []
        for datetype in ("edat", "pdat"):
            try:
                params = {
                    "db": "pubmed",
                    "term": term,
                    "datetype": datetype,
                    "retmax": retmax,
                    "sort": "pub date",
                }
                if target_date:
                    day = target_date.strftime("%Y/%m/%d")
                    params["mindate"] = day
                    params["maxdate"] = day
                else:
                    params["reldate"] = 1 if hours <= 24 else max(1, round(hours / 24))
                result = self._read_with_retries(Entrez.esearch, **params)
                ids = [str(item) for item in result.get("IdList", [])]
                self.logger.info("Search datetype=%s returned %s PMIDs for query: %s", datetype, len(ids), query)
                found.extend(ids)
            except Exception as exc:
                self.logger.exception("Search failed for datetype=%s query=%s: %s", datetype, query, exc)
        return list(dict.fromkeys(found))

    def fetch_papers(self, pmids: list[str], batch_size: int = 100) -> dict[str, Paper]:
        papers: dict[str, Paper] = {}
        for start in range(0, len(pmids), batch_size):
            batch = pmids[start : start + batch_size]
            if not batch:
                continue
            try:
                records = self._read_with_retries(
                    Entrez.efetch,
                    db="pubmed",
                    id=",".join(batch),
                    retmode="xml",
                )
                for article in records.get("PubmedArticle", []):
                    paper = self._parse_article(article)
                    papers[paper.pmid] = paper
            except Exception as exc:
                self.logger.exception("Failed to fetch PubMed batch starting at %s: %s", start, exc)
        return papers

    def _parse_article(self, record: dict[str, Any]) -> Paper:
        citation = record.get("MedlineCitation", {})
        article = citation.get("Article", {})
        pubmed_data = record.get("PubmedData", {})
        pmid = clean_text(citation.get("PMID", ""))
        title = clean_text(article.get("ArticleTitle", ""))
        journal = clean_text(article.get("Journal", {}).get("Title", ""))
        publication_date = self._extract_publication_date(article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {}))
        indexed_date = self._extract_history_date(pubmed_data.get("History", []), preferred=("pubmed", "medline", "received", "accepted"))
        doi = self._extract_doi(article, pubmed_data)
        abstract = self._extract_abstract(article)
        authors = self._extract_authors(article.get("AuthorList", []))
        return Paper(
            pmid=pmid,
            title=title,
            journal=journal,
            publication_date=publication_date,
            indexed_date=indexed_date,
            doi=doi,
            abstract=abstract,
            authors=authors,
            pubmed_link=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            abstract_missing=not bool(abstract),
        )

    def _extract_publication_date(self, pub_date: dict[str, Any]) -> str:
        if not pub_date:
            return "未提供"
        if "MedlineDate" in pub_date:
            return clean_text(pub_date.get("MedlineDate"))
        parts = [clean_text(pub_date.get(key, "")) for key in ("Year", "Month", "Day")]
        return " ".join(part for part in parts if part) or "未提供"

    def _extract_history_date(self, history: list[Any], preferred: tuple[str, ...]) -> str:
        seen: dict[str, str] = {}
        for item in history or []:
            status = clean_text(item.attributes.get("PubStatus", "") if hasattr(item, "attributes") else "")
            year = clean_text(item.get("Year", ""))
            month = clean_text(item.get("Month", ""))
            day = clean_text(item.get("Day", ""))
            if status and year:
                seen[status.lower()] = "-".join(part.zfill(2) if part.isdigit() and len(part) == 1 else part for part in (year, month, day) if part)
        for status in preferred:
            if status in seen:
                return seen[status]
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _extract_doi(self, article: dict[str, Any], pubmed_data: dict[str, Any]) -> str:
        ids: list[Any] = []
        ids.extend(article.get("ELocationID", []) or [])
        ids.extend(pubmed_data.get("ArticleIdList", []) or [])
        for item in ids:
            id_type = clean_text(item.attributes.get("EIdType", "") if hasattr(item, "attributes") else "")
            if not id_type:
                id_type = clean_text(item.attributes.get("IdType", "") if hasattr(item, "attributes") else "")
            if id_type.lower() == "doi":
                return clean_text(item)
        return "未提供"

    def _extract_abstract(self, article: dict[str, Any]) -> str:
        abstract = article.get("Abstract", {}).get("AbstractText", [])
        parts = []
        for part in abstract:
            label = clean_text(part.attributes.get("Label", "") if hasattr(part, "attributes") else "")
            text = clean_text(part)
            if label and text:
                parts.append(f"{label}: {text}")
            elif text:
                parts.append(text)
        return " ".join(parts)

    def _extract_authors(self, author_list: list[Any]) -> list[str]:
        authors: list[str] = []
        for author in author_list or []:
            collective = clean_text(author.get("CollectiveName", ""))
            if collective:
                authors.append(collective)
                continue
            last = clean_text(author.get("LastName", ""))
            fore = clean_text(author.get("ForeName", ""))
            if last or fore:
                authors.append(" ".join(part for part in (fore, last) if part))
        return authors
