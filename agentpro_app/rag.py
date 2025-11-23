import os, hashlib, re
from typing import List, Dict, Optional, Tuple
from pypdf import PdfReader
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import numpy as np

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_embedder = SentenceTransformer(EMBED_MODEL)

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "vectorstore")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(allow_reset=False))

# In-memory BM25 index per collection (for prototype)
bm25_indexes = {}

def _collection_name(user_id: str, course_id: str) -> str:
    """Generate a unique collection name for user+course."""
    raw = f"{user_id}:{course_id}"
    h = hashlib.sha1(raw.encode()).hexdigest()[:24]
    return f"sb_{h}"

def ensure_collection(user_id: str, course_id: str):
    """Get or create a Chroma collection for a user's course."""
    name = _collection_name(user_id, course_id)
    try:
        return chroma_client.get_collection(name=name)
    except Exception:
        return chroma_client.create_collection(
            name=name, 
            metadata={"user_id": user_id, "course_id": course_id}
        )

def extract_sentences(text: str) -> List[str]:
    """Split text into sentences for better chunking."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def semantic_chunk(text: str, target_size: int = 1000, overlap: int = 500) -> List[str]:
    """
    Chunk by sentence boundaries with overlap.
    More intelligent than fixed-character chunking.
    """
    sentences = extract_sentences(text)
    chunks = []
    current = []
    current_len = 0
    
    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len > target_size and current:
            chunks.append(" ".join(current))
            
            # Keep last sentences for overlap
            overlap_sents = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current = overlap_sents
            current_len = overlap_len
        
        current.append(sent)
        current_len += sent_len
    
    if current:
        chunks.append(" ".join(current))
    
    return chunks

def pdf_to_chunks(path: str) -> List[Dict]:
    """
    Enhanced PDF chunking with metadata.
    Extracts text page-by-page, then chunks intelligently.
    """
    reader = PdfReader(path)
    chunks: List[Dict] = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = " ".join(text.split())  # Normalize whitespace
        
        if not text:
            continue
            
        page_chunks = semantic_chunk(text, target_size=1000, overlap=500)
        
        for chunk_idx, chunk in enumerate(page_chunks):
            chunks.append({
                "page": i + 1,
                "text": chunk,
                "chunk_idx": chunk_idx,
                "char_count": len(chunk)
            })
    
    return chunks

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    embeddings = _embedder.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()

def upsert_pdf(user_id: str, course_id: str, doc_id: str, title: str, path: str) -> Dict:
    """
    Improved PDF ingestion with BM25 indexing.
    Processes PDF → chunks → embeddings → stores in Chroma + builds BM25 index.
    """
    col = ensure_collection(user_id, course_id)
    chunks = pdf_to_chunks(path)
    
    if not chunks:
        return {"doc_id": doc_id, "chunks": 0}

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metas = [
        {
            "doc_id": doc_id, 
            "title": title, 
            "page": c["page"],
            "chunk_idx": c["chunk_idx"],
            "char_count": c["char_count"]
        } 
        for c in chunks
    ]
    texts = [c["text"] for c in chunks]
    vecs = embed_texts(texts)
    
    # Upsert into Chroma
    col.upsert(ids=ids, embeddings=vecs, documents=texts, metadatas=metas)
    
    # Build/update BM25 index for keyword search
    col_name = _collection_name(user_id, course_id)
    
    # Fetch all existing documents for BM25
    try:
        all_data = col.get(include=["documents", "metadatas"])
        all_texts = all_data["documents"]
        all_ids = all_data["ids"]
        all_metas = all_data["metadatas"]
        
        tokenized = [text.lower().split() for text in all_texts]
        bm25_indexes[col_name] = {
            "index": BM25Okapi(tokenized),
            "ids": all_ids,
            "texts": all_texts,
            "metas": all_metas
        }
    except Exception as e:
        print(f"Warning: Could not build BM25 index: {e}")
    
    return {"doc_id": doc_id, "chunks": len(chunks)}

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot_product / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0

def mmr_deduplicate(results: List[Dict], lambda_param: float = 0.7, top_k: int = 8) -> List[Dict]:
    """
    Maximal Marginal Relevance for diversity.
    Balances relevance and diversity to avoid redundant chunks.
    """
    if len(results) <= top_k:
        return results
    
    selected = [results[0]]  # Start with highest scored
    remaining = results[1:]
    
    while len(selected) < top_k and remaining:
        best_score = -float('inf')
        best_idx = 0
        
        for idx, candidate in enumerate(remaining):
            # Relevance score
            relevance = candidate['score']
            
            # Max similarity to already selected (for diversity penalty)
            max_sim = 0.0
            if '_vec' in candidate:
                for sel in selected:
                    if '_vec' in sel:
                        sim = cosine_similarity(candidate['_vec'], sel['_vec'])
                        max_sim = max(max_sim, sim)
            
            # MMR score: high relevance, low similarity to selected
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        
        selected.append(remaining[best_idx])
        remaining.pop(best_idx)
    
    return selected

def hybrid_retrieve(
    user_id: str, 
    course_id: str, 
    query: str, 
    k: int = 8,
    alpha: float = 0.7,  # Weight for dense vs BM25 (0.7 = 70% dense, 30% BM25)
    threshold: float = 0.3,  # Minimum similarity threshold
    use_mmr: bool = True
) -> List[Dict]:
    """
    Hybrid retrieval: dense embeddings + BM25 keyword search + MMR deduplication.
    
    Returns chunks with enhanced metadata including:
    - text: full chunk text
    - meta: {doc_id, title, page, chunk_idx, char_count}
    - score: fusion score (combined dense + BM25)
    - snippet: preview of text
    - source: "dense" | "bm25" | "both"
    """
    col = ensure_collection(user_id, course_id)
    col_name = _collection_name(user_id, course_id)
    
    # 1. Dense retrieval (semantic search)
    qvec = embed_texts([query])[0]
    dense_results = col.query(
        query_embeddings=[qvec], 
        n_results=k * 2,  # Over-retrieve for fusion
        include=["documents", "metadatas", "distances", "embeddings"]
    )
    
    dense_hits = []
    if dense_results["ids"] and dense_results["ids"][0]:
        for i in range(len(dense_results["ids"][0])):
            score = 1.0 - float(dense_results["distances"][0][i])
            if score >= threshold:
                dense_hits.append({
                    "id": dense_results["ids"][0][i],
                    "text": dense_results["documents"][0][i],
                    "meta": dense_results["metadatas"][0][i],
                    "score": score,
                    "source": "dense",
                    "_vec": dense_results["embeddings"][0][i] if "embeddings" in dense_results else []
                })
    
    # 2. BM25 retrieval (keyword search)
    bm25_hits = []
    if col_name in bm25_indexes:
        bm25_data = bm25_indexes[col_name]
        tokenized_query = query.lower().split()
        bm25_scores = bm25_data["index"].get_scores(tokenized_query)
        
        # Get top K BM25 results
        top_indices = np.argsort(bm25_scores)[::-1][:k * 2]
        
        for idx in top_indices:
            if bm25_scores[idx] > 0:
                bm25_hits.append({
                    "id": bm25_data["ids"][idx],
                    "text": bm25_data["texts"][idx],
                    "meta": bm25_data["metas"][idx],
                    "score": float(bm25_scores[idx]) / (max(bm25_scores) + 1e-6),  # Normalize
                    "source": "bm25"
                })
    
    # 3. Fusion: combine and re-rank by weighted scores
    combined = {}
    for hit in dense_hits:
        combined[hit["id"]] = {
            **hit,
            "fusion_score": alpha * hit["score"]
        }
    
    for hit in bm25_hits:
        if hit["id"] in combined:
            # Both dense and BM25 found this chunk
            combined[hit["id"]]["fusion_score"] += (1 - alpha) * hit["score"]
            combined[hit["id"]]["source"] = "both"
        else:
            # Only BM25 found this
            combined[hit["id"]] = {
                **hit,
                "fusion_score": (1 - alpha) * hit["score"]
            }
    
    # Sort by fusion score
    results = sorted(combined.values(), key=lambda x: x["fusion_score"], reverse=True)
    
    # 4. Apply MMR for diversity if requested
    if use_mmr:
        results = mmr_deduplicate(results, lambda_param=0.7, top_k=k)
    else:
        results = results[:k]
    
    # 5. Format output with snippets
    output = []
    for r in results:
        snippet = r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"]
        output.append({
            "text": r["text"],
            "meta": r["meta"],
            "score": r.get("fusion_score", r["score"]),
            "snippet": snippet,
            "source": r.get("source", "unknown")
        })
    
    return output

def retrieve(user_id: str, course_id: str, query: str, k: int = 8) -> List[Dict]:
    """
    Simple retrieve function (backward compatible).
    Calls hybrid_retrieve under the hood.
    """
    return hybrid_retrieve(user_id, course_id, query, k=k)

def get_collection_stats(user_id: str, course_id: str) -> Dict:
    """Get statistics about the collection."""
    try:
        col = ensure_collection(user_id, course_id)
        all_data = col.get(include=["metadatas"])
        
        doc_ids = set()
        total_chunks = len(all_data["ids"])
        
        for meta in all_data["metadatas"]:
            doc_ids.add(meta.get("doc_id", "unknown"))
        
        return {
            "total_documents": len(doc_ids),
            "total_chunks": total_chunks,
            "doc_ids": list(doc_ids)
        }
    except Exception as e:
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "doc_ids": [],
            "error": str(e)
        }