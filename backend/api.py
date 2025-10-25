from livekit.agents import llm
from livekit.agents.llm import FunctionContext
import faiss, pickle, numpy as np, os
from openai import OpenAI

IDX_PATH = "../rag/faiss.index"
META_PATH = "../rag/meta.pkl"
EMBED_MODEL = "text-embedding-3-small"
SIM_THRESH = 0.28
TOP_K = 5

class AssistantFnc(FunctionContext):
    def __init__(self):
        super().__init__()
        if not (os.path.exists(IDX_PATH) and os.path.exists(META_PATH)):
            raise RuntimeError("RAG index missing for MEDLINE. Run `python ingest.py`.")
        self.idx = faiss.read_index(IDX_PATH)
        self.meta = pickle.load(open(META_PATH, "rb"))
        self.client = OpenAI()

    def _catalog(self):
        cat = {}
        for m in self.meta:
            if m.get("file") not in cat:
                cat[m.get("file")] = m.get("source_id", "S?")
        return cat

    @llm.ai_callable(name="health_doc_catalog", description="Get mapping of MEDLINE files to citation ids like S1, S2.")
    async def health_doc_catalog(self) -> str:
        cat = self._catalog()
        lines = [f"{sid}: {fn}" for fn, sid in sorted(cat.items(), key=lambda x: x[1])]
        return "\n".join(lines)

    @llm.ai_callable(name="health_doc_search", description="Retrieve top-k MEDLINE snippets with citation ids [S#].")
    async def health_doc_search(self, query: str, k: int = TOP_K) -> str:
        q = self.client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
        q = np.array([q], dtype="float32"); faiss.normalize_L2(q)
        D, I = self.idx.search(q, int(k))
        pairs = [(float(d), int(i)) for d, i in zip(D[0], I[0]) if i != -1 and float(d) >= SIM_THRESH]
        if not pairs:
            return ""
        blocks = []
        for d, i in pairs:
            m = self.meta[i]
            sid = m.get("source_id", "S?")
            blocks.append(f"[{sid}] score={d:.2f}\n{m['text']}")
        return "\n\n---\n\n".join(blocks)

    @llm.ai_callable(name="health_answer", description="Answer strictly from MEDLINE docs with [S#] citations or refuse.")
    async def health_answer(self, query: str, max_sentences: int = 5) -> str:
        q = (query or "").strip()
        if not q or len(q.split()) < 2:
            return "REFUSE: Please ask a specific question about the MEDLINE documents."

        ctx = await self.health_doc_search(q, k=TOP_K)
        if not ctx:
            return ("REFUSE: I don’t have that information in the provided MEDLINE documents. "
                    "I can connect you with a healthcare professional for further help.")

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
