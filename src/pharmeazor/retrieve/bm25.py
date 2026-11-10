"""A small, dependency-free BM25 ranker.

Present so the repository has a working keyword baseline from day one: the
dense retriever is compared *against* this, with figures, rather than adopted on
faith. Keyword search misses rephrasings; semantic search sometimes conflates
two drugs with similar names. The evaluation set decides which wins where.

Reference: Robertson & Zaragoza, "The Probabilistic Relevance Framework:
BM25 and Beyond" (2009).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

__all__ = ["tokenize", "BM25Index", "ScoredPassage"]

# Very common French words carry no discriminating signal for this corpus.
_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "et", "ou", "a",
    "au", "aux", "en", "dans", "pour", "par", "sur", "avec", "sans", "est",
    "sont", "ce", "cet", "cette", "ces", "il", "elle", "on", "que", "qui",
    "quel", "quelle", "ne", "pas", "plus", "peut", "doit", "se", "son", "sa",
}


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    """Lowercase, de-accent, split on non-letters, drop stopwords.

    Numbers are kept: a dose is often the most discriminating token in a query.
    """
    normalised = _strip_accents(text.lower())
    tokens = re.findall(r"[a-z0-9]+", normalised)
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


@dataclass(frozen=True)
class ScoredPassage:
    """One retrieval hit."""

    passage_id: str
    score: float
    text: str


@dataclass
class BM25Index:
    """An in-memory BM25 index over passages.

    Args:
        k1: Term-frequency saturation. Higher means repeated terms keep adding.
        b: Length normalisation, 0 (off) to 1 (full).
    """

    k1: float = 1.5
    b: float = 0.75

    _ids: list[str] = field(default_factory=list, repr=False)
    _texts: list[str] = field(default_factory=list, repr=False)
    _tokens: list[list[str]] = field(default_factory=list, repr=False)
    _freqs: list[Counter] = field(default_factory=list, repr=False)
    _doc_freq: Counter = field(default_factory=Counter, repr=False)
    _avg_len: float = field(default=0.0, repr=False)

    def add(self, passage_id: str, text: str) -> None:
        """Index one passage. Call :meth:`finalize` once all are added."""
        tokens = tokenize(text)
        self._ids.append(passage_id)
        self._texts.append(text)
        self._tokens.append(tokens)
        self._freqs.append(Counter(tokens))
        for term in set(tokens):
            self._doc_freq[term] += 1

    def finalize(self) -> BM25Index:
        """Compute the average document length. Returns self for chaining."""
        if self._tokens:
            self._avg_len = sum(len(t) for t in self._tokens) / len(self._tokens)
        return self

    def _idf(self, term: str) -> float:
        n = len(self._tokens)
        df = self._doc_freq.get(term, 0)
        # Robertson/Sparck Jones IDF, floored at zero to avoid negative weights.
        return max(0.0, math.log(1 + (n - df + 0.5) / (df + 0.5)))

    def search(self, query: str, top_k: int = 8) -> list[ScoredPassage]:
        """Rank indexed passages against ``query``, best first."""
        if not self._tokens:
            return []
        if self._avg_len == 0.0:
            self.finalize()

        query_terms = tokenize(query)
        results: list[ScoredPassage] = []

        for i, freqs in enumerate(self._freqs):
            length = len(self._tokens[i])
            total = 0.0
            for term in query_terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                denominator = tf + self.k1 * (1 - self.b + self.b * length / self._avg_len)
                total += self._idf(term) * (tf * (self.k1 + 1)) / denominator
            if total > 0:
                results.append(ScoredPassage(self._ids[i], round(total, 6), self._texts[i]))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def __len__(self) -> int:
        return len(self._ids)
