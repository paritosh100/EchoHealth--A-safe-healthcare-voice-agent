# RAG Pipeline Upgrade — Session Notes

What changed, why, and how it was actually validated (not assumed).

## What we started with

Single-stage dense retrieval: embed the query, FAISS cosine search, keep anything
above a static `SIM_THRESH = 0.28`, stuff the top-5 into a citation prompt. One gate,
one number.

## What we built, in order, and why

### 1. Query Rewriting
An LLM (`gpt-4o-mini`) cleans the raw query before it hits retrieval — fixes ASR noise,
expands abbreviations. EchoHealth is voice-first, so the query text comes from speech
transcription, not typed input; this step exists specifically for that.

### 2. Hybrid Search (FAISS + BM25)
Dense vector search alone blurs short/exact terms. Added BM25 keyword search alongside
FAISS, fused via reciprocal rank fusion (`rag_utils.py`).

### 3. Reranking
A local cross-encoder (`ms-marco-MiniLM-L-6-v2`) re-scores the fused candidates for
true relevance before keeping the real top-5. No API cost, runs on CPU.

### 4. Corrective RAG
After retrieval, an LLM grades whether the context actually answers the question
(not just "is it above a similarity number"). If weak, retries once with a
reformulated query before falling back to the existing REFUSE message.

### 5. Parent-Child Retrieval (added after a real failure was found — see below)
Small chunks (1200 chars) are what get embedded and matched for precision, but each
small chunk now belongs to a larger parent section (3600 chars). The final context
sent to the grader/generator resolves back up to the parent, deduped — so an answer
isn't built from a fragment that got cut off mid-explanation.

## How we proved any of this actually helped

First instinct ("let's just test it by talking to it") was called out, correctly —
one or two voice queries can't demonstrate improvement, only measurement can.

**`eval.py`** — 15 easy, single-topic golden queries (one per MEDLINE file).
Result: **old and new pipelines tied, 100% vs 100%.** Honest finding: the corpus
(10 well-separated documents) is too easy to discriminate between the two pipelines
on simple questions. This is real evidence of *no proven difference* on easy queries,
not a wasted test.

**`eval_hard.py`** — adversarial queries built by actually grepping the indexed chunk
text for exact clinical terms unique to one document (`LDL`, `A1C`, `systolic`,
`autoimmune`). Result: **old 86% (6/7) vs new 100% (7/7).** The real failure case:
*"what is LDL cholesterol"* returned **zero results** from the old dense-only pipeline
(below the 0.28 threshold — would have silently REFUSED a valid question) while the
new hybrid pipeline retrieved the correct document via exact keyword match.

**Observability caught a second-order bug.** Adding per-stage logging (`[rag][req-id]`,
stdlib `logging`, no new dependency) surfaced that the *same* LDL query that won on
retrieval (correct doc in top-5) still got REFUSED by the full `health_answer` flow —
because Corrective RAG's grading step judged the actual 1200-char chunk text
insufficient to answer the question, even though the right document was found.
Recall (doc-level) and groundedness (content-level) are different bars. This
specific finding is what motivated Parent-Child Retrieval — the fix for a chunking
problem, not a retrieval-tuning problem.

## Unrelated but real bugs fixed along the way

- **System clock ~1 year behind** on the dev machine caused every minted JWT to be
  born already-expired by LiveKit Cloud's clock → 401 on every connection attempt.
- **Hardcoded dead JWT** literally pasted into `LiveKitModal.jsx`, overriding the live
  fetched token — meant fixing the clock alone didn't fix the 401, because the UI
  wasn't even using the real token.
- **LiveKit SDK (`livekit-agents` 0.12.4) outdated** — OpenAI shut down the Realtime
  Beta API it depended on (`beta_api_shape_disabled`). Upgraded to `1.8.6`, which is a
  breaking rewrite: `FunctionContext` → `Agent` subclass, `@llm.ai_callable` →
  `@function_tool`, `MultimodalAgent` + manual event wiring → `AgentSession` +
  `session.start()`/`generate_reply()`. RAG logic inside was untouched by this.
- **Assistant greeted in Korean unprompted** — `INSTRUCTIONS` never pinned a response
  language, so the realtime model picked one on its own. Fixed with one explicit rule.

## What's still open

- Real in-process latency hasn't been measured yet (the one captured trace was a cold
  process: CrossEncoder first-load + two full retry passes = 12.8s, worse-case, not
  representative of a warm `agent.py` session).
- `eval.py`/`eval_hard.py` are standalone scripts, not wired into CI — re-run manually
  after any retrieval/prompt change, don't trust memory of "it worked before."
