import os, pickle, numpy as np, faiss
from bs4 import BeautifulSoup
from pypdf import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

DOC_DIR = "../docs"
OUT_DIR = "../rag"
IDX_PATH = os.path.join(OUT_DIR, "faiss.index")
META_PATH = os.path.join(OUT_DIR, "meta.pkl")
EMBED_MODEL = "text-embedding-3-small"

def read_html_text(path: str) -> str:
    html = open(path, encoding="utf-8", errors="ignore").read()
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return soup.get_text(separator="\n")

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
    meta, vecs = [], []
    for full_path, source_id, text in iter_docs():
        base = os.path.basename(full_path)
        for c in chunk(text):
            emb = client.embeddings.create(model=EMBED_MODEL, input=c).data[0].embedding
            vecs.append(emb)
            meta.append({"file": base, "source_id": source_id, "text": c})
    if not vecs:
        raise RuntimeError(f"No documents found under {DOC_DIR}")
    arr = np.array(vecs, dtype="float32"); faiss.normalize_L2(arr)
    idx = faiss.IndexFlatIP(arr.shape[1]); idx.add(arr)
    faiss.write_index(idx, IDX_PATH); pickle.dump(meta, open(META_PATH, "wb"))
    print(f"Indexed {len(meta)} chunks from {len(set(m['file'] for m in meta))} files into {OUT_DIR}")

if __name__ == "__main__":
    main()
