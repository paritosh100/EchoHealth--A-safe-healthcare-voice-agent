import os, pickle, numpy as np, faiss
from bs4 import BeautifulSoup
from pypdf import PdfReader
from openai import OpenAI
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
load_dotenv()

DOC_DIR = "../docs"
OUT_DIR = "../rag"
IDX_PATH = os.path.join(OUT_DIR, "faiss.index")
META_PATH = os.path.join(OUT_DIR, "meta.pkl")
BM25_PATH = os.path.join(OUT_DIR, "bm25.pkl")
PARENT_PATH = os.path.join(OUT_DIR, "parents.pkl")
EMBED_MODEL = "text-embedding-3-small"
PARENT_CHUNK_SIZE = 3600
PARENT_CHUNK_OVERLAP = 400
CHILD_CHUNK_SIZE = 1200
CHILD_CHUNK_OVERLAP = 200

def read_html_text(path: str) -> str:
    html = open(path, encoding="utf-8", errors="ignore").read()
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    # MedlinePlus pages wrap real article prose in <article>; the rest of the page
    # is nav menus and "related topics" link lists that were polluting every chunk.
    main = soup.select_one("article") or soup
    return main.get_text(separator="\n")

def iter_docs():
    html_files = []
    items = []
    for r, _, fs in os.walk(DOC_DIR):
        for f in fs:
            p = os.path.join(r, f)
            if f.lower().endswith(".html"):
                html_files.append(p)
            elif f.lower().endswith(".pdf"):
                t = ""
                for pg in PdfReader(p).pages:
                    t += pg.extract_text() or ""
                items.append((p, os.path.basename(p), t))
            elif f.lower().endswith((".md", ".txt")):
                items.append((p, os.path.basename(p), open(p, encoding="utf-8", errors="ignore").read()))
    html_files.sort()
    for i, p in enumerate(html_files, start=1):
        text = read_html_text(p)
        items.append((p, f"S{i}", text))
    return items  # (full_path, source_id_or_filename, text)

def chunk(s, size=1200, overlap=200):
    out = []
    i = 0
    while i < len(s):
        out.append(s[i:i+size])
        i += size - overlap
    return out

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    client = OpenAI()
    meta, vecs, parents = [], [], []
    for full_path, source_id, text in iter_docs():
        base = os.path.basename(full_path)
        # Parent-child retrieval: embed/index small child chunks for precise matching,
        # but keep their larger parent section around so answers aren't built from a
        # fragment that got cut off mid-explanation.
        for p_text in chunk(text, size=PARENT_CHUNK_SIZE, overlap=PARENT_CHUNK_OVERLAP):
            parent_id = len(parents)
            parents.append({"file": base, "source_id": source_id, "text": p_text})
            for c in chunk(p_text, size=CHILD_CHUNK_SIZE, overlap=CHILD_CHUNK_OVERLAP):
                emb = client.embeddings.create(model=EMBED_MODEL, input=c).data[0].embedding
                vecs.append(emb)
                meta.append({"file": base, "source_id": source_id, "text": c, "parent_id": parent_id})
    if not vecs:
        raise RuntimeError(f"No documents found under {DOC_DIR}")
    arr = np.array(vecs, dtype="float32"); faiss.normalize_L2(arr)
    idx = faiss.IndexFlatIP(arr.shape[1]); idx.add(arr)
    faiss.write_index(idx, IDX_PATH); pickle.dump(meta, open(META_PATH, "wb"))
    pickle.dump(parents, open(PARENT_PATH, "wb"))

    bm25 = BM25Okapi([m["text"].lower().split() for m in meta])
    pickle.dump(bm25, open(BM25_PATH, "wb"))

    print(f"Indexed {len(meta)} child chunks ({len(parents)} parents) from "
          f"{len(set(m['file'] for m in meta))} files into {OUT_DIR}")

if __name__ == "__main__":
    main()
