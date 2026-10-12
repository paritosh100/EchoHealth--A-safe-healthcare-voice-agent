"""Adversarial Recall@5: queries engineered to expose where dense-only retrieval
fails and hybrid+rerank should win -- exact clinical terms, cross-topic term overlap,
and semantic/lexical mismatches found by inspecting the actual indexed chunks.
Run: python eval_hard.py
"""
import faiss
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from api import AssistantFnc

# (query, expected_source_id, why_its_hard)
GOLDEN = [
    ("what is LDL cholesterol", "S5",
     "LDL is lexically unique to Heart Disease, but 'cholesterol' also appears in Nutrition (S8) -- tests exact-term precision"),
    ("what does an A1C test measure", "S4",
     "A1C is lexically unique to Diabetes -- exact clinical abbreviation, easy for BM25, harder for embeddings to weight"),
    ("what counts as a high systolic reading", "S6",
     "systolic is lexically unique to Hypertension -- precise clinical term"),
    ("is type 1 diabetes an autoimmune condition", "S4",
     "the literal word 'autoimmune' only appears in the Heart Disease chunk (S5), not Diabetes (S4) -- "
     "correct answer requires understanding the concept, not matching the word"),
    ("which foods raise cholesterol levels", "S8",
     "cholesterol appears in both Heart Disease (S5) and Nutrition (S8) -- 'foods' should disambiguate toward Nutrition"),
    ("how do vaccines help your immune system make antibodies", "S10",
     "antibodies/antibod appears in both Diabetes (S4) and Vaccines (S10) -- context should disambiguate toward Vaccines"),
    ("what is insulin resistance", "S4",
     "exact phrase unique to Diabetes, phrased plainly -- control case, should be easy for both"),
]

SIM_THRESH = 0.28


def old_dense_search(assistant: AssistantFnc, query: str, k: int = 5) -> list[str]:
    emb = assistant.client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    q = np.array([emb], dtype="float32")
    faiss.normalize_L2(q)
    D, I = assistant.idx.search(q, k)
    return [assistant.meta[int(i)].get("source_id", "S?") for d, i in zip(D[0], I[0]) if i != -1 and float(d) >= SIM_THRESH]


def new_hybrid_rerank(assistant: AssistantFnc, query: str, k: int = 5) -> list[str]:
    rewritten = assistant._rewrite_query(query)
    fused = assistant._hybrid_retrieve(rewritten)
    top = assistant._rerank(rewritten, fused, top_n=k)
    return [assistant.meta[i].get("source_id", "S?") for i in top]


def main():
    a = AssistantFnc()
    old_hits, new_hits = 0, 0
    print(f"{'query':55} {'expect':7} {'old@5':8} {'new@5':8}")
    print("-" * 90)
    for query, expected, why in GOLDEN:
        old_sids = old_dense_search(a, query)
        new_sids = new_hybrid_rerank(a, query)
        old_ok = expected in old_sids
        new_ok = expected in new_sids
        old_hits += old_ok
        new_hits += new_ok
        print(f"{query[:54]:55} {expected:7} {('OK' if old_ok else 'MISS'):8} {('OK' if new_ok else 'MISS'):8}")
        print(f"  -> old: {old_sids}  new: {new_sids}")
        print(f"  -> why: {why}")
        print()

    n = len(GOLDEN)
    print("-" * 90)
    print(f"Recall@5  old (dense-only threshold): {old_hits}/{n} = {old_hits/n:.0%}")
    print(f"Recall@5  new (hybrid + rerank):       {new_hits}/{n} = {new_hits/n:.0%}")


if __name__ == "__main__":
    main()
