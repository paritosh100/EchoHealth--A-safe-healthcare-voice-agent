from livekit.agents import Agent, function_tool
import faiss, pickle, numpy as np, os, logging, time, uuid, contextvars
from openai import OpenAI
from sentence_transformers import CrossEncoder
from rag_utils import reciprocal_rank_fusion
from prompts import INSTRUCTIONS

logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)

_req_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("rag_req_id", default="-")


def _log(msg: str, *args) -> None:
    logger.info(f"[rag][{_req_id_var.get()}] " + msg, *args)

IDX_PATH = "../rag/faiss.index"
META_PATH = "../rag/meta.pkl"
BM25_PATH = "../rag/bm25.pkl"
PARENT_PATH = "../rag/parents.pkl"
EMBED_MODEL = "text-embedding-3-small"
REWRITE_MODEL = "gpt-4o-mini"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
FUSION_K = 15   # candidates pulled from dense+sparse before reranking
TOP_K = 5        # final chunks kept after reranking

class AssistantFnc(Agent):
    def __init__(self):
        super().__init__(instructions=INSTRUCTIONS)
        if not (os.path.exists(IDX_PATH) and os.path.exists(META_PATH) and os.path.exists(BM25_PATH) and os.path.exists(PARENT_PATH)):
            raise RuntimeError("RAG index missing for MEDLINE. Run `python ingest.py`.")
        self.idx = faiss.read_index(IDX_PATH)
        self.meta = pickle.load(open(META_PATH, "rb"))
        self.bm25 = pickle.load(open(BM25_PATH, "rb"))
        self.parents = pickle.load(open(PARENT_PATH, "rb"))
        self.client = OpenAI()
        self.reranker = CrossEncoder(RERANK_MODEL)
        self._last_rerank_score: float | None = None

    def _catalog(self):
        cat = {}
        for m in self.meta:
            if m.get("file") not in cat:
                cat[m.get("file")] = m.get("source_id", "S?")
        return cat

    @function_tool(name="health_doc_catalog", description="Get mapping of MEDLINE files to citation ids like S1, S2.")
    async def health_doc_catalog(self) -> str:
        cat = self._catalog()
        lines = [f"{sid}: {fn}" for fn, sid in sorted(cat.items(), key=lambda x: x[1])]
        return "\n".join(lines)

    def _rewrite_query(self, raw_query: str) -> str:
        """Clean up ASR/voice transcription noise into a tight search query."""
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=REWRITE_MODEL,
            temperature=0,
            max_tokens=40,
            messages=[{
                "role": "system",
                "content": (
                    "Rewrite this voice-transcribed health question into a clean search "
                    "query. Fix ASR errors, expand abbreviations, keep it under 20 words. "
                    "Output only the rewritten query, nothing else."
                ),
            }, {"role": "user", "content": raw_query}],
        )
        rewritten = resp.choices[0].message.content.strip() or raw_query
        _log("rewrite %.0fms: %r -> %r", (time.perf_counter() - t0) * 1000, raw_query, rewritten)
        return rewritten

    def _hybrid_retrieve(self, query: str, k: int = FUSION_K) -> list[int]:
        """Dense (FAISS) + sparse (BM25) retrieval fused via reciprocal rank fusion."""
        t0 = time.perf_counter()
        q_emb = self.client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
        q_emb = np.array([q_emb], dtype="float32"); faiss.normalize_L2(q_emb)
        _, dense_idx = self.idx.search(q_emb, k)
        dense_ranks = [int(i) for i in dense_idx[0] if i != -1]

        bm25_scores = self.bm25.get_scores(query.lower().split())
        sparse_ranks = [int(i) for i in np.argsort(bm25_scores)[::-1][:k]]

        fused = reciprocal_rank_fusion([dense_ranks, sparse_ranks])
        _log(
            "hybrid_retrieve %.0fms: dense=%s sparse=%s fused_top=%s",
            (time.perf_counter() - t0) * 1000, dense_ranks[:5], sparse_ranks[:5], fused[:5],
        )
        return fused

    def _rerank(self, query: str, candidate_idx: list[int], top_n: int = TOP_K) -> list[int]:
        """Cross-encoder re-score of fused candidates down to the real top-n."""
        if not candidate_idx:
            _log("rerank skipped: no candidates")
            self._last_rerank_score = None
            return []
        t0 = time.perf_counter()
        pairs = [(query, self.meta[i]["text"]) for i in candidate_idx]
        scores = self.reranker.predict(pairs)
        ranked = [i for _, i in sorted(zip(scores, candidate_idx), key=lambda x: x[0], reverse=True)]
        top = ranked[:top_n]
        sids = [self.meta[i].get("source_id", "S?") for i in top]
        top_score = float(max(scores)) if len(scores) else None
        self._last_rerank_score = top_score  # confidence proxy, read by health_answer for the summary line
        _log("rerank %.0fms: kept=%s top_score=%.3f", (time.perf_counter() - t0) * 1000, sids, top_score or 0.0)
        return top

    def _format_chunks(self, indices: list[int]) -> str:
        """Parent-child retrieval: resolve each matched (small) child chunk up to its
        larger parent section, deduped, so the model sees full context instead of a
        fragment that may have been cut off mid-explanation."""
        seen_parents: list[int] = []
        for i in indices:
            pid = self.meta[i].get("parent_id")
            if pid is not None and pid not in seen_parents:
                seen_parents.append(pid)
        blocks = []
        for pid in seen_parents:
            p = self.parents[pid]
            blocks.append(f"[{p.get('source_id', 'S?')}]\n{p['text']}")
        return "\n\n---\n\n".join(blocks)

    @function_tool(name="health_doc_search", description="Retrieve top-k MEDLINE snippets with citation ids [S#].")
    async def health_doc_search(self, query: str, k: int = TOP_K) -> str:
        standalone = _req_id_var.get() == "-"
        token = _req_id_var.set(uuid.uuid4().hex[:8]) if standalone else None
        t0 = time.perf_counter()
        try:
            query = self._rewrite_query(query)
            fused = self._hybrid_retrieve(query)
            top = self._rerank(query, fused, top_n=int(k))
            result = self._format_chunks(top)
            if standalone:
                _log("SUMMARY total=%.0fms confidence=%.3f chunks=%d",
                     (time.perf_counter() - t0) * 1000, self._last_rerank_score or 0.0, len(top))
            return result
        finally:
            if token is not None:
                _req_id_var.reset(token)

    def _context_is_relevant(self, query: str, ctx: str) -> bool:
        """Grade whether retrieved context actually answers the query (Corrective RAG)."""
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=REWRITE_MODEL,
            temperature=0,
            max_tokens=3,
            messages=[{
                "role": "system",
                "content": (
                    "Given a question and retrieved passages, reply YES if the passages "
                    "contain enough information to answer accurately, otherwise NO. "
                    "Reply with only YES or NO."
                ),
            }, {"role": "user", "content": f"Question: {query}\n\nPassages:\n{ctx}"}],
        )
        verdict = resp.choices[0].message.content.strip().upper().startswith("Y")
        _log("grade %.0fms: relevant=%s", (time.perf_counter() - t0) * 1000, verdict)
        return verdict

    @function_tool(name="health_answer", description="Answer strictly from MEDLINE docs with [S#] citations or refuse.")
    async def health_answer(self, query: str, max_sentences: int = 5) -> str:
        token = _req_id_var.set(uuid.uuid4().hex[:8])
        t0 = time.perf_counter()
        try:
            return await self._health_answer_impl(query, max_sentences, t0)
        finally:
            _req_id_var.reset(token)

    async def _health_answer_impl(self, query: str, max_sentences: int, t0: float) -> str:
        q = (query or "").strip()
        if not q or len(q.split()) < 2:
            return "REFUSE: Please ask a specific question about the MEDLINE documents."

        REFUSE_MSG = ("REFUSE: I don’t have that information in the provided MEDLINE documents. "
                      "I can connect you with a healthcare professional for further help.")

        ctx = await self.health_doc_search(q, k=TOP_K)
        confidence = self._last_rerank_score or 0.0
        if ctx and not self._context_is_relevant(q, ctx):
            _log("corrective: weak context, retrying with reformulated query")
            ctx = ""  # weak context: force the retry path below

        if not ctx:
            retry_query = self._rewrite_query(f"Previous search for '{q}' found nothing useful. Try a different phrasing.")
            fused = self._hybrid_retrieve(retry_query)
            top = self._rerank(retry_query, fused, top_n=TOP_K)
            ctx = self._format_chunks(top)
            confidence = self._last_rerank_score or 0.0
            if ctx and not self._context_is_relevant(q, ctx):
                _log("corrective: retry still weak, refusing")
                ctx = ""

        if not ctx:
            _log("SUMMARY total=%.0fms confidence=%.3f outcome=REFUSE query=%r",
                 (time.perf_counter() - t0) * 1000, confidence, q)
            return REFUSE_MSG

        _log("SUMMARY total=%.0fms confidence=%.3f outcome=ANSWERED query=%r",
             (time.perf_counter() - t0) * 1000, confidence, q)

        clean_ctx = []
        for block in ctx.split("---"):
            lines = [ln for ln in block.strip().split("\n") if ln.strip()]
            if lines and lines[0].startswith("[") and "]" in lines[0]:
                sid_line = lines[0].split("]")[0] + "]"
                lines = [sid_line] + lines[1:]
            clean_ctx.append("\n".join(lines))
        context = "\n\n".join(clean_ctx)

        return (
            "You are a Health Information Assistant.\n"
            "Rules:\n"
            "- Use ONLY the context below from MEDLINE documents.\n"
            "- Provide general information; DO NOT diagnose or recommend treatments.\n"
            "- If asked for diagnosis/treatment/personal advice, respond: "
            "\"I can’t provide medical advice. Please consult a qualified healthcare professional.\" "
            "and offer to connect them.\n"
            "- Use plain language and short sentences.\n"
            "- Include [S#] citations inline. When speaking, say “According to [S#] …”.\n"
            "- If unsure or not found, state that and offer to connect the user with a specialist.\n"
            f"- Limit to {max_sentences} sentences.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {q}\n\n"
            "Write the final answer now."
        )
