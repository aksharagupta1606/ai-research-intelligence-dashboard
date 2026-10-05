from __future__ import annotations

import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.text_utils import split_sentences

TOPIC_TERMS = {
    "Artificial Intelligence": ["artificial intelligence", "intelligent system", "ai model"],
    "Machine Learning": ["machine learning", "supervised learning", "unsupervised learning"],
    "Deep Learning": ["deep learning", "neural network", "transformer", "representation learning"],
    "Natural Language Processing": ["natural language", "language model", "text", "linguistic", "nlp"],
    "Computer Vision": ["computer vision", "image", "visual", "object detection", "segmentation"],
    "Data Science": ["data science", "analytics", "data mining", "statistical"],
    "Healthcare AI": ["healthcare", "clinical", "medical", "patient", "diagnosis"],
    "Cybersecurity": ["cybersecurity", "security", "intrusion", "malware", "privacy"],
    "Climate & Environmental AI": ["climate", "environment", "weather", "emission", "sustainability"],
    "Robotics": ["robot", "robotics", "autonomous", "manipulation", "navigation"],
}

DOMAIN_STOPWORDS = {
    "study", "paper", "research", "result", "results", "method", "methods", "approach",
    "proposed", "propose", "using", "based", "new", "also", "however", "show", "shows",
    "demonstrate", "demonstrates", "work", "works", "problem", "data", "model", "models",
}
STOPWORDS = set(ENGLISH_STOP_WORDS).union(DOMAIN_STOPWORDS)


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text or "", flags=re.I)
    text = re.sub(r"\b(?:doi:)?10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", " ", text, flags=re.I)
    text = re.sub(r"[^A-Za-z0-9\s.,;:!?'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", clean_text(text).lower())


def remove_stopwords(tokens: list[str]) -> list[str]:
    return [word for word in tokens if word not in STOPWORDS and len(word) > 2]


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    content = clean_text(text)
    if not content:
        return []
    try:
        vectorizer = TfidfVectorizer(
            stop_words=list(STOPWORDS), ngram_range=(1, 2), max_features=1500,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b",
        )
        matrix = vectorizer.fit_transform([content])
        values = matrix.toarray()[0]
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(values, terms), reverse=True)
        return [term for score, term in ranked if score > 0][:limit]
    except ValueError:
        return []


def generate_summary(text: str, sentence_count: int = 3) -> str:
    sentences = split_sentences(clean_text(text))
    if not sentences:
        return "Not enough readable text to create a summary."
    if len(sentences) <= sentence_count:
        return " ".join(sentences)
    try:
        matrix = TfidfVectorizer(stop_words=list(STOPWORDS)).fit_transform(sentences)
        importance = np.asarray(matrix.sum(axis=1)).ravel()
        chosen = sorted(np.argsort(importance)[-sentence_count:].tolist())
        return " ".join(sentences[index] for index in chosen)
    except ValueError:
        return " ".join(sentences[:sentence_count])


def calculate_similarity(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0))
    try:
        matrix = TfidfVectorizer(stop_words=list(STOPWORDS), ngram_range=(1, 2)).fit_transform(texts)
        return cosine_similarity(matrix)
    except ValueError:
        return np.zeros((len(texts), len(texts)))


def classify_topic(text: str) -> list[str]:
    content = clean_text(text).lower()
    scored = []
    for topic, terms in TOPIC_TERMS.items():
        score = sum(content.count(term) for term in terms)
        if score:
            scored.append((score, topic))
    return [topic for _, topic in sorted(scored, reverse=True)[:3]] or ["Data Science"]


def extract_methodology(text: str) -> str:
    terms = (
        "experiment", "survey", "case study", "randomized", "benchmark", "ablation",
        "cross-validation", "qualitative", "quantitative", "simulation", "systematic review",
        "comparative", "regression", "interview",
    )
    matches = [term for term in terms if re.search(rf"\b{re.escape(term)}\w*\b", text, re.I)]
    return ", ".join(matches[:5]) or "Methodology not explicitly identifiable from the available text."


def extract_future_work(text: str) -> str:
    sentences = split_sentences(text)
    cues = ("future work", "future research", "further study", "next step", "remain to be", "should be explored")
    matches = [sentence for sentence in sentences if any(cue in sentence.lower() for cue in cues)]
    return " ".join(matches[:3]) or "No explicit future-work statement detected."


def detect_potential_gaps(text: str, topic: str | None = None) -> list[str]:
    sentences = split_sentences(text)
    cues = ("limitation", "limited", "lack of", "underrepresented", "remains unclear", "future work", "further research")
    gaps = [sentence for sentence in sentences if any(cue in sentence.lower() for cue in cues)]
    if gaps:
        return gaps[:4]
    topic_label = topic or classify_topic(text)[0]
    return [
        f"Potential gap to validate: broader evaluation of {topic_label.lower()} across diverse datasets.",
        f"Potential gap to validate: reproducibility and external validation for methods in {topic_label.lower()}.",
    ]


def extract_section(text: str, cue_words: tuple[str, ...]) -> str:
    sentences = split_sentences(text)
    matches = [sentence for sentence in sentences if any(cue in sentence.lower() for cue in cue_words)]
    return " ".join(matches[:3]) or "Not explicitly identified in the available text."


def keyword_frequency(texts: list[str], limit: int = 10) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(set(extract_keywords(text, limit=16)))
    return counts.most_common(limit)