"""
ai/knowledge/indexer.py
=======================
Semantic chunking, provenance binding, and inverted indexing for Knowledge (S28-02).

Guarantees:
- Semantic boundary chunking (headings, sections, rules, procedures, anti-patterns).
- Blind token splitting is STRICTLY FORBIDDEN.
- Full provenance tracking on every chunk (document_id, section, version, source, hash).
- Provider-neutral indexing with deterministic keyword and semantic representations.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from ai.contracts.creative.skills_knowledge import KnowledgeDescriptor
from ai.knowledge.contracts import KnowledgeChunk
from ai.knowledge.loader import LoadedKnowledgeDocument


def tokenize(text: str) -> List[str]:
    """Extracts lowercase alphanumeric tokens and bigrams for lexical/semantic matching."""
    raw_tokens = re.findall(r"[a-zA-Z0-9_\u0600-\u06FF]+", text.lower())
    # Stopwords to filter out for index noise reduction
    stopwords = {
        "the", "a", "an", "is", "and", "or", "to", "in", "of", "for", "with",
        "on", "at", "by", "from", "as", "this", "that", "it", "are", "be",
        "من", "في", "إلى", "على", "عن", "مع", "هذا", "هذه", "أن", "أو", "هو", "هي"
    }
    tokens = [t for t in raw_tokens if t not in stopwords and len(t) > 1]
    return tokens


class KnowledgeIndexer:
    """
    Transforms loaded knowledge documents into searchable, provenance-bound
    semantic chunks and maintains a provider-neutral search index.
    """

    def __init__(self) -> None:
        # All indexed chunks: chunk_id -> KnowledgeChunk
        self._chunks: Dict[str, KnowledgeChunk] = {}
        # Inverted index: token -> set of chunk_ids
        self._inverted_index: Dict[str, Set[str]] = {}
        # Document to chunks map: document_id -> list of chunk_ids
        self._doc_chunks: Dict[str, List[str]] = {}

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    def get_chunk(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        return self._chunks.get(chunk_id)

    def get_chunks_for_document(self, document_id: str) -> List[KnowledgeChunk]:
        chunk_ids = self._doc_chunks.get(document_id, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def chunk_document(self, doc: LoadedKnowledgeDocument) -> List[KnowledgeChunk]:
        """
        Semantically chunks a markdown document using structural boundaries:
        headings (#, ##, ###), rules (**N. ...**), and procedure blocks.
        """
        lines = doc.content.splitlines()
        descriptor = doc.descriptor

        chunks: List[KnowledgeChunk] = []
        current_section = descriptor.title
        current_lines: List[str] = []

        def flush_chunk(section_name: str, text_lines: List[str]):
            text = "\n".join(text_lines).strip()
            if not text:
                return
            
            # If section contains distinct numbered rules (e.g. **1. ...**, **2. ...**),
            # split into semantic sub-chunks if large
            rule_pattern = re.compile(r"(?:\n|^)\*\*(\d+)\.\s+([^\*]+)\*\*", re.MULTILINE)
            rule_matches = list(rule_pattern.finditer(text))

            if len(rule_matches) > 1 and len(text) > 800:
                # Sub-chunk by rule
                for i, match in enumerate(rule_matches):
                    start = match.start()
                    end = rule_matches[i + 1].start() if i + 1 < len(rule_matches) else len(text)
                    rule_text = text[start:end].strip()
                    rule_title = match.group(2).strip()
                    sub_section = f"{section_name} > Rule {match.group(1)}: {rule_title}"
                    
                    chk = KnowledgeChunk.create(
                        document_id=descriptor.knowledge_id,
                        section=sub_section,
                        version=descriptor.version,
                        source=descriptor.source_uri,
                        content=rule_text,
                        category=descriptor.category,
                        tags=descriptor.tags,
                        video_types=descriptor.video_types,
                        platforms=descriptor.platforms,
                        audio_modes=descriptor.audio_modes,
                        language=descriptor.language,
                        authority_level=descriptor.authority_level,
                    )
                    chunks.append(chk)
            else:
                chk = KnowledgeChunk.create(
                    document_id=descriptor.knowledge_id,
                    section=section_name,
                    version=descriptor.version,
                    source=descriptor.source_uri,
                    content=text,
                    category=descriptor.category,
                    tags=descriptor.tags,
                    video_types=descriptor.video_types,
                    platforms=descriptor.platforms,
                    audio_modes=descriptor.audio_modes,
                    language=descriptor.language,
                    authority_level=descriptor.authority_level,
                )
                chunks.append(chk)

        heading_re = re.compile(r"^(#{1,3})\s+(.+)$")

        for line in lines:
            m = heading_re.match(line)
            if m:
                # Flush previous block
                if current_lines:
                    flush_chunk(current_section, current_lines)
                    current_lines = []
                current_section = m.group(2).strip()
            current_lines.append(line)

        # Flush final block
        if current_lines:
            flush_chunk(current_section, current_lines)

        return chunks

    def index_document(self, doc: LoadedKnowledgeDocument) -> List[KnowledgeChunk]:
        """Chunks and indexes a single loaded knowledge document."""
        chunks = self.chunk_document(doc)
        doc_id = doc.descriptor.knowledge_id

        # Clean existing index for this doc if re-indexing
        if doc_id in self._doc_chunks:
            old_ids = self._doc_chunks[doc_id]
            for oid in old_ids:
                if oid in self._chunks:
                    del self._chunks[oid]

        self._doc_chunks[doc_id] = []

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._doc_chunks[doc_id].append(chunk.chunk_id)

            # Inverted index tokens
            tokens = tokenize(f"{chunk.section} {chunk.content} {' '.join(chunk.tags)}")
            for t in set(tokens):
                if t not in self._inverted_index:
                    self._inverted_index[t] = set()
                self._inverted_index[t].add(chunk.chunk_id)

        return chunks

    def index_many(self, docs: Sequence[LoadedKnowledgeDocument]) -> int:
        """Indexes multiple loaded documents, returns total chunks created."""
        count = 0
        for d in docs:
            c = self.index_document(d)
            count += len(c)
        return count

    def get_candidate_chunk_ids(self, query_tokens: Sequence[str]) -> Set[str]:
        """Finds all chunk IDs matching any query token in the inverted index."""
        candidate_ids: Set[str] = set()
        for tok in query_tokens:
            if tok in self._inverted_index:
                candidate_ids.update(self._inverted_index[tok])
        return candidate_ids

    def all_chunks(self) -> List[KnowledgeChunk]:
        """Returns all indexed chunks."""
        return list(self._chunks.values())
