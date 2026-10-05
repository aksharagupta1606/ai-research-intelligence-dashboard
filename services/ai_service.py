from __future__ import annotations

import json

import requests

from config.settings import AI_API_KEY, AI_BASE_URL, AI_MODEL
from services import nlp_service
from utils.logger import logger


def _local_analysis(text: str) -> dict:
    topics = nlp_service.classify_topic(text)
    return {
        "source": "NLP-generated analysis",
        "summary": nlp_service.generate_summary(text, 2),
        "detailed_summary": nlp_service.generate_summary(text, 5),
        "keywords": nlp_service.extract_keywords(text),
        "topics": topics,
        "methodology": nlp_service.extract_methodology(text),
        "dataset": nlp_service.extract_section(text, ("dataset", "data set", "cohort", "benchmark", "corpus")),
        "findings": nlp_service.extract_section(text, ("we find", "results show", "results indicate", "our results", "findings")),
        "limitations": nlp_service.extract_section(text, ("limitation", "limited by", "challenge", "constraint")),
        "future_work": nlp_service.extract_future_work(text),
        "research_gaps": nlp_service.detect_potential_gaps(text, topics[0]),
    }


def analyze_paper(text: str) -> dict:
    """Use an optional OpenAI-compatible endpoint; fall back to local, key-free NLP."""
    fallback = _local_analysis(text)
    if not AI_API_KEY or not text.strip():
        return fallback
    prompt = (
        "Analyze the supplied research-paper text. Return only a JSON object with keys "
        "summary, detailed_summary, keywords (array), topics (array), methodology, dataset, "
        "findings, limitations, future_work, research_gaps (array). Treat gaps as tentative "
        "and say they require expert validation. Do not invent facts.\n\n"
        f"Paper text:\n{text[:16000]}"
    )
    try:
        response = requests.post(
            f"{AI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": AI_MODEL,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=35,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        return {"source": "AI-assisted analysis", **fallback, **parsed}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.warning("Optional AI request failed; using local NLP analysis.")
        return fallback


def summarize_paper(text: str) -> str:
    return str(analyze_paper(text).get("summary", ""))


def identify_research_gaps(text: str) -> list[str]:
    return list(analyze_paper(text).get("research_gaps", []))


def generate_research_questions(topic: str, gaps: list[str], papers: list[dict]) -> list[dict]:
    paper_names = [paper.get("title", "Selected literature") for paper in papers[:3]]
    directions = [
        "A comparative evaluation across multiple datasets",
        "A mixed-methods study with domain experts",
        "A prospective validation with uncertainty reporting",
        "A fairness and subgroup robustness audit",
        "A reproducibility study using an open benchmark",
    ]
    questions = []
    for index in range(5):
        gap = gaps[index % len(gaps)] if gaps else f"Limited evidence about {topic.lower()} in varied real-world settings."
        questions.append(
            {
                "question": f"How does {topic.lower()} perform when {directions[index].lower()}?",
                "gap": gap,
                "papers": paper_names,
                "methodology": directions[index],
                "label": "AI-generated suggestion — validate with domain experts",
            }
        )
    return questions


def compare_papers(papers: list[dict]) -> dict:
    texts = [f"{paper.get('title', '')} {paper.get('abstract', '')}" for paper in papers]
    matrix = nlp_service.calculate_similarity(texts)
    keywords = [set(nlp_service.extract_keywords(text, 12)) for text in texts]
    common = sorted(set.intersection(*keywords)) if keywords else []
    unique = [sorted(keys.difference(*(keywords[:i] + keywords[i + 1 :]))) for i, keys in enumerate(keywords)]
    return {"similarity": matrix.tolist(), "common_keywords": common, "unique_keywords": unique}