"""Golden-set Recall@5 comparison: old dense-only retrieval vs new hybrid+rerank pipeline.
Run: python eval.py
"""
import faiss
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from api import AssistantFnc

# (query, expected_source_id) -- spans all 10 MEDLINE files, phrased with ASR-style noise
GOLDEN = [
    ("what is asthma and what triggers it", "S1"),
    ("um like what causes an asthma attack", "S1"),
    ("what are the different types of cancer", "S2"),
    ("signs of depression", "S3"),
    ("uh what's the difference between type 1 and type 2 diabetes", "S4"),
    ("what increases risk of heart disease", "S5"),
    ("what is considered high blood pressure", "S6"),
    ("hypertension risk factors", "S6"),
    ("what do kidneys do and what is kidney disease", "S7"),
    ("what is good nutrition", "S8"),
    ("obesity health risks", "S9"),
    ("why are vaccines important", "S10"),
    ("what is immunization", "S10"),
    ("warning signs of a heart attack", "S5"),
    ("how to manage type 1 diabetes", "S4"),
]

SIM_THRESH = 0.28


def old_dense_search(assistant: AssistantFnc, query: str, k: int = 5) -> list[str]:
    """Replicates the pre-upgrade dense-only FAISS search with static threshold."""
    emb = assistant.client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    q = np.array([emb], dtype="float32")
    faiss.normalize_L2(q)
    D, I = assistant.idx.search(q, k)
    sids = []
    for d, i in zip(D[0], I[0]):
        if i != -1 and float(d) >= SIM_THRESH:
            sids.append(assistant.meta[int(i)].get("source_id", "S?"))
    return sids


def new_hybrid_rerank(assistant: AssistantFnc, query: str, k: int = 5) -> list[str]:
    rewritten = assistant._rewrite_query(query)
    fused = assistant._hybrid_retrieve(rewritten)
    top = assistant._rerank(rewritten, fused, top_n=k)
    return [assistant.meta[i].get("source_id", "S?") for i in top]


def main():
    a = AssistantFnc()
    old_hits, new_hits = 0, 0
    print(f"{'query':50} {'expect':6} {'old top-5':30} {'new top-5':30}")
    print("-" * 120)
    for query, expected in GOLDEN:
        old_sids = old_dense_search(a, query)
        new_sids = new_hybrid_rerank(a, query)
        old_ok = expected in old_sids
        new_ok = expected in new_sids
        old_hits += old_ok
        new_hits += new_ok
        mark_old = "OK" if old_ok else "MISS"
        mark_new = "OK" if new_ok else "MISS"
        print(f"{query[:49]:50} {expected:6} {str(old_sids)+' '+mark_old:30} {str(new_sids)+' '+mark_new:30}")

    n = len(GOLDEN)
    print("-" * 120)
    print(f"Recall@5  old (dense-only threshold): {old_hits}/{n} = {old_hits/n:.0%}")
    print(f"Recall@5  new (hybrid + rerank):       {new_hits}/{n} = {new_hits/n:.0%}")


if __name__ == "__main__":
    main()
