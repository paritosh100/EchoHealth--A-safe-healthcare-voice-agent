def reciprocal_rank_fusion(rank_lists: list[list[int]], k: int = 60) -> list[int]:
    """Fuse multiple ranked index lists (best-first) into one ranking via RRF."""
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)
