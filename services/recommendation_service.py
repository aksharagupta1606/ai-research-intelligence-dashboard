from __future__ import annotations

import numpy as np

from services.nlp_service import calculate_similarity


def similar_papers(target, papers, limit: int = 5) -> list[tuple[object, float]]:
    candidates = [paper for paper in papers if paper.id != target.id]
    texts = [f"{paper.title} {paper.abstract}" for paper in [target, *candidates]]
    matrix = calculate_similarity(texts)
    scores = matrix[0, 1:] if matrix.size else np.array([])
    ranked = sorted(zip(scores, candidates), reverse=True, key=lambda item: item[0])
    return [(paper, float(score)) for score, paper in ranked[:limit]]