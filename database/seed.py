from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select

from database.database import SessionLocal, init_db
from database.models import Author, Paper, PaperAnalysis, Topic, Keyword
from services.nlp_service import (
    classify_topic,
    detect_potential_gaps,
    extract_keywords,
    extract_methodology,
    extract_section,
    extract_future_work,
    generate_summary,
)
from utils.text_utils import split_authors


DEMO_PAPERS = [
    ("Interpretable Machine Learning for Clinical Decision Support", 2024, "Maya Chen; Daniel Brooks", "Healthcare AI", "Journal of Illustrative Clinical AI", 182, "Clinical decision support models can improve triage, but clinicians need explanations they can inspect. We compare sparse linear models with gradient-boosted trees and calibrated neural networks across three de-identified hospital datasets. A prospective workflow study measures decision time, confidence, and error patterns. Results show that concise feature explanations improve review speed without increasing override rates. The study is limited by a single health-system context. Future work should test the interface with rural clinics and larger language models."),
    ("Robust Vision Transformers Under Distribution Shift", 2023, "Elena Rossi; Arjun Mehta", "Computer Vision", "Proceedings of the Demo Vision Research Forum", 146, "This benchmark evaluates vision transformers when camera, lighting, and background distributions shift between training and deployment. We measure calibration error and accuracy on six public image collections. Augmentation improves average robustness, while domain-specific fine-tuning remains effective when labels are scarce. The benchmark does not cover video streams or uncommon sensor hardware. Future research should study online adaptation with safety constraints."),
    ("Low-Resource Language Models for Public-Service Translation", 2025, "Priya Nair; Samuel Okafor; Lila Mensah", "Natural Language Processing", "Illustrative Transactions on Language Technology", 91, "We investigate multilingual transfer for public-service translation in eight low-resource languages. The approach combines parallel-corpus filtering, instruction tuning, and human review. Evaluation includes terminology accuracy and community-rated fluency. Results indicate that targeted data curation can outperform simply scaling model size. The available corpora underrepresent dialectal variation. Further research should examine consent-led data collection and robustness to code switching."),
    ("Federated Learning for Privacy-Preserving Radiology", 2022, "Nora Patel; Miguel Santos", "Healthcare AI", "Demo Journal of Medical Computing", 228, "Hospitals often cannot pool imaging data because of privacy and governance requirements. This study compares federated averaging, secure aggregation, and locally trained baselines on chest-image classification. Cross-site evaluation finds a modest improvement in recall with federation, but performance varies with scanner protocol. The experiments use a small number of institutions. Future work should test fairness and communication cost across regional hospital networks."),
    ("Graph Neural Networks for Urban Traffic Forecasting", 2024, "Hannah Kim; Elias Turner", "Machine Learning", "Illustrative Smart Cities Review", 134, "We propose a graph neural network that combines road connectivity with time-of-day and weather features to predict corridor-level traffic. Evaluation uses two city sensor networks and reports lower peak-hour error than recurrent baselines. Ablation tests highlight the value of incident signals. Sparse sensors in peripheral neighborhoods remain a limitation. Future research should assess transfer to cities with different road layouts."),
    ("Explainable Malware Detection with Program Graphs", 2021, "Omar Haddad; Grace Miller", "Cybersecurity", "Proceedings of the Sample Security Symposium", 204, "This work represents executable behavior as a program graph and compares graph neural networks with signature and tree-based detectors. Explanations identify suspicious call paths and file operations for analyst review. The model improves recall on a time-separated test set, though obfuscation still reduces performance. The dataset is dominated by desktop software. Further study should include mobile and embedded malware."),
    ("Satellite Learning for Regional Climate Risk Mapping", 2025, "Lucia Fernandez; Wei Zhang", "Climate & Environmental AI", "Demo Environmental Data Science Letters", 77, "We fuse multispectral satellite observations with historical rainfall to estimate regional flood exposure. A convolutional model is evaluated against geospatial baselines across four watersheds. Estimates align with surveyed flood extents and improve where ground sensors are sparse. Cloud cover and uneven survey coverage affect confidence. Future work should combine community reports with uncertainty-aware forecasting."),
    ("Safe Sim-to-Real Transfer for Warehouse Robotics", 2023, "Noah Williams; Aisha Rahman", "Robotics", "Illustrative Robotics Research", 116, "We study policy transfer from simulation to a small warehouse robot fleet under changing payload and floor conditions. Randomized simulation plus a safety monitor reduces collision events during staged trials. The approach is tested in a controlled facility with limited human traffic. Future work should extend the evaluation to longer deployments and mixed robot fleets."),
    ("Topic Discovery in Scientific Abstract Collections", 2020, "Isabel García; James Osei", "Data Science", "Sample Journal of Research Analytics", 318, "This paper compares non-negative matrix factorization, probabilistic topic models, and embedding clusters for organizing scientific abstracts. Human reviewers assess coherence and label stability across repeated samples. Hybrid embeddings improve semantic grouping but retain sensitivity to corpus size. The evaluation focuses on English-language abstracts. Future research should measure usefulness for interdisciplinary discovery."),
    ("Self-Supervised Speech Recognition for Noisy Field Recordings", 2024, "Fatima Ali; Peter Novak", "Deep Learning", "Demo Speech and Audio Systems", 103, "We adapt self-supervised acoustic representations to noisy field recordings collected in transport and outdoor settings. The method combines masked prediction with targeted augmentation and is compared with supervised baselines. Word error rates improve for low-volume speech, while overlapping speakers remain difficult. The recordings cover a limited set of accents. Further research should explore privacy-preserving personalization."),
    ("Fairness Audits for Automated Loan Risk Models", 2022, "Chloe Martin; Ravi Iyer", "Artificial Intelligence", "Illustrative Journal of Responsible Computing", 261, "We present a repeatable audit workflow for comparing group calibration, error rates, and counterfactual sensitivity in loan-risk models. Tests across three synthetic and public datasets show that aggregate accuracy can conceal substantial subgroup gaps. The workflow helps teams document mitigation trade-offs. The analysis cannot capture every jurisdiction-specific constraint. Future work should evaluate how audit findings change real lending decisions."),
    ("Compact Segmentation Models for Edge Devices", 2023, "Kai Nakamura; Sofia Petrova", "Computer Vision", "Demo Applied Vision Systems", 155, "This study evaluates compact segmentation architectures for edge devices used in roadside monitoring. Quantized models are compared on latency, memory, and boundary accuracy under low light. Structured pruning reduces compute while maintaining useful segmentation quality. Hardware support differs substantially across devices. Future work should study energy use during continuous operation."),
    ("Retrieval-Augmented Question Answering for Scientific Literature", 2025, "Daniel Brooks; Maya Chen; Yuki Tanaka", "Natural Language Processing", "Illustrative Journal of Digital Scholarship", 68, "We evaluate retrieval-augmented generation for answering questions over scientific abstracts and full-text passages. The system combines section-aware retrieval with citation verification and is compared against closed-book prompting. Evidence attribution improves when passages are short and metadata is complete. The evaluation set contains few contradictory findings. Future work should test expert workflows and calibrated abstention."),
    ("Anomaly Detection for Industrial Sensor Streams", 2021, "Rafael Costa; Emily Shaw", "Machine Learning", "Sample Industrial Informatics", 239, "We compare density estimation, isolation forests, and temporal convolutional models for anomaly detection in industrial sensor streams. Evaluation uses chronological splits to reflect deployment conditions. Temporal features improve early warning for recurring equipment faults. Rare failure labels and changing maintenance practices remain limitations. Further research should measure false-alarm costs with operators."),
    ("Privacy Risks in Clinical Text De-identification", 2024, "Leila Haddad; Thomas Reed", "Cybersecurity", "Demo Privacy Engineering Journal", 86, "This analysis measures residual identifier risk after applying rule-based and transformer-based clinical note de-identification. A red-team evaluation finds stronger recall for uncommon names with context-aware models, but demographic disparities remain. The study relies on a narrow collection of note styles. Future work should test multilingual records and governance procedures for model updates."),
    ("Predicting Crop Water Stress from Multispectral Imagery", 2022, "Ananya Rao; Mateo Silva", "Climate & Environmental AI", "Illustrative Journal of Agricultural Intelligence", 174, "We use multispectral imagery and local weather to estimate crop water stress before visible damage occurs. A temporal convolutional model is compared with vegetation-index thresholds across two growing seasons. Early warning improves in irrigated plots, while cloudy periods reduce coverage. Smallholder farms are underrepresented. Future research should assess low-cost sensors and farmer-led validation."),
    ("Human-Robot Collaboration in Small-Batch Manufacturing", 2025, "Aisha Rahman; Noah Williams", "Robotics", "Sample Manufacturing Systems", 59, "This work studies task allocation between operators and collaborative robots on short production runs. A contextual policy adapts to workcell congestion and operator feedback. Simulation and a pilot assembly line show fewer idle intervals than fixed scheduling. The trial is brief and involves experienced operators. Future work should include novice users and ergonomic outcomes."),
    ("Weakly Supervised Detection of Rare Cardiac Events", 2023, "Miguel Santos; Priya Nair", "Healthcare AI", "Demo Journal of Biomedical Signals", 197, "We combine weak labels from clinical notes with electrocardiogram windows to detect rare cardiac events. The model is assessed with patient-level splits and compared against a fully supervised baseline. Weak supervision increases case coverage without a large annotation effort. Label noise and differences in monitoring equipment remain limitations. Further research should evaluate calibration in emergency settings."),
    ("Causal Discovery for Public Health Intervention Data", 2020, "James Osei; Fatima Ali", "Data Science", "Illustrative Public Health Methods", 284, "We examine constraint-based and score-based causal discovery methods for observational public health data. Synthetic experiments and a carefully reviewed case study show that domain constraints improve graph stability. Unmeasured confounding remains difficult to rule out. The case study is not sufficient to establish intervention effects. Future research should compare discovery with prospective study designs."),
    ("Efficient Attention for Long-Document Summarization", 2024, "Yuki Tanaka; Elena Rossi", "Deep Learning", "Demo Journal of Language Models", 121, "We compare sparse and recurrent attention strategies for summarizing long technical documents. Evaluation combines factual consistency checks with expert ratings of coverage. Sparse attention offers a useful latency-quality trade-off on mid-sized reports. Performance declines for documents with dense tables and cross-references. Future work should include multimodal reports and citation-aware evaluation."),
    ("Detecting Phishing Campaigns Through Email Graphs", 2022, "Grace Miller; Omar Haddad", "Cybersecurity", "Illustrative Network Security Letters", 213, "We model sender-recipient and domain relationships as a temporal graph to detect coordinated phishing campaigns. Graph features are compared with content-only classifiers on a chronological split. Network context helps identify repeated infrastructure, but adversaries can rotate domains. The data omits some encrypted channels. Further research should test privacy-preserving collaboration between organizations."),
    ("Coastal Flood Mapping with Uncertainty-Aware Segmentation", 2025, "Wei Zhang; Lucia Fernandez", "Climate & Environmental AI", "Sample Journal of Climate Informatics", 64, "This paper proposes uncertainty-aware segmentation for coastal flood extent from satellite imagery. The model reports confidence maps alongside predicted water boundaries and is evaluated after several storm events. Confidence estimates are useful for prioritizing manual review. Validation is sparse for small islands and informal settlements. Future work should improve coverage through local observation networks."),
    ("Learning Dexterous Manipulation from Demonstrations", 2021, "Elias Turner; Kai Nakamura", "Robotics", "Demo Robotics and Automation", 192, "We investigate learning-based manipulation from human demonstrations with visual and tactile feedback. A policy is tested on object transfer tasks under changes in shape and friction. Tactile signals improve success on deformable objects. The robot platform and object set are limited. Further research should examine sim-to-real transfer and safe recovery from failed grasps."),
    ("Evaluating Synthetic Data for Rare Disease Research", 2024, "Sofia Petrova; Leila Haddad", "Healthcare AI", "Illustrative Journal of Health Data", 109, "We assess synthetic tabular data for improving rare-disease prediction when records cannot be widely shared. Utility, privacy leakage, and subgroup coverage are measured across several generation methods. Synthetic augmentation helps for selected conditions but can reproduce underrepresented patterns. The results depend on the source cohort. Future studies should involve patient advocates in evaluation."),
    ("Multimodal Sentiment Analysis in Online Learning", 2023, "Samuel Okafor; Chloe Martin", "Natural Language Processing", "Sample Educational Technology Research", 148, "We study text and audio cues for identifying learner frustration during online tutoring sessions. A multimodal classifier is compared with text-only and audio-only models using consented recordings. Audio contributes most when chat is sparse, but performance varies by language background. The participant sample is small. Further research should evaluate privacy-preserving feedback and learner control."),
    ("Automated Defect Inspection with Few-Shot Vision Models", 2025, "Arjun Mehta; Hannah Kim", "Computer Vision", "Demo Journal of Smart Manufacturing", 72, "We evaluate few-shot visual inspection for product defects when only a small number of labelled examples are available. The approach combines pretrained image embeddings and a calibrated nearest-neighbor classifier. Results are promising on held-out defect types, but reflective surfaces remain challenging. Future research should test real production drift and operator review procedures."),
    ("Adaptive Resource Allocation in Edge Analytics", 2022, "Emily Shaw; Rafael Costa", "Data Science", "Illustrative Edge Computing Review", 185, "This study introduces a workload scheduler that balances latency, battery use, and network congestion for edge analytics. It is evaluated in a simulated sensor network and a small laboratory deployment. Adaptive batching lowers average energy demand under variable traffic. The field deployment is too small to assess long-term reliability. Future work should include adversarial network conditions."),
    ("Benchmarking Retrieval Systems for Legal Documents", 2021, "Thomas Reed; Isabel García", "Artificial Intelligence", "Sample Information Retrieval Studies", 246, "We compare sparse retrieval, dense embeddings, and hybrid ranking for searching legal documents. Evaluation includes relevance judgments and citation recall across multiple query types. Hybrid search performs consistently, while dense retrieval helps with paraphrased questions. The benchmark is limited to one legal system and language. Further work should study expert-assisted relevance labeling."),
    ("Forecasting Renewable Energy Output with Weather Ensembles", 2024, "Mateo Silva; Ananya Rao", "Machine Learning", "Demo Journal of Sustainable Systems", 131, "We combine weather ensembles and historical generation to forecast short-term solar and wind output. Probabilistic forecasts are compared with point predictions across seasonal splits. Ensemble inputs improve uncertainty calibration during rapidly changing conditions. Performance is weaker for new installations with little history. Future research should assess transfer learning across regions."),
    ("Active Learning for Safer Autonomous Navigation", 2025, "Peter Novak; Nora Patel", "Robotics", "Illustrative Autonomous Systems Journal", 83, "We evaluate active learning for selecting difficult navigation scenarios in a simulated and small-scale robot environment. A risk-weighted query strategy improves collision prediction with fewer labelled episodes than random sampling. The evaluation excludes dense pedestrian environments. Future work should examine human feedback, safe exploration, and deployment monitoring."),
]


def _get_or_create(session, model, field: str, value: str):
    instance = session.scalar(select(model).where(getattr(model, field) == value))
    if instance is None:
        instance = model(**{field: value})
        session.add(instance)
        session.flush()
    return instance


def seed_database() -> int:
    init_db()
    session = SessionLocal()
    try:
        inserted = 0
        for record in DEMO_PAPERS:
            title, year, authors, topic_name, journal, citations, abstract = record
            paper = session.scalar(select(Paper).where(Paper.title == title))
            if paper is None:
                paper = Paper(
                    title=title,
                    abstract=abstract,
                    publication_year=year,
                    journal=journal,
                    doi=None,
                    url=None,
                    citation_count=citations,
                    source="Demo dataset — illustrative record",
                )
                session.add(paper)
                session.flush()
                inserted += 1
            if not paper.authors:
                paper.authors = [_get_or_create(session, Author, "name", name) for name in split_authors(authors)]
            topic_names = list(dict.fromkeys([topic_name, *classify_topic(f"{title} {abstract}")[:2]]))
            if not paper.topics:
                paper.topics = [_get_or_create(session, Topic, "name", name) for name in topic_names]
            keywords = extract_keywords(f"{title}. {abstract}", limit=7)
            if not paper.keywords:
                paper.keywords = [_get_or_create(session, Keyword, "keyword", keyword) for keyword in keywords]
            analysis_values = {
                "summary": generate_summary(abstract, 2),
                "detailed_summary": generate_summary(abstract, 4),
                "methodology": "Local keyword extraction: " + extract_methodology(abstract),
                "dataset": extract_section(abstract, ("dataset", "data set", "cohort", "benchmark", "corpus")),
                "findings": extract_section(abstract, ("results show", "results indicate", "we find", "our results")),
                "limitations": extract_section(
                    abstract,
                    ("limitation", "limited by", "remain difficult", "underrepresented", "challenge"),
                ),
                "future_work": extract_future_work(abstract),
                "research_gaps": "\n".join(detect_potential_gaps(abstract, topic_name)),
            }
            if not paper.analyses:
                session.add(PaperAnalysis(paper_id=paper.id, **analysis_values))
            elif paper.source.startswith("Demo dataset") and len(paper.analyses) == 1:
                # Refresh only the original sample analysis; keep any later user-created analyses intact.
                for field, value in analysis_values.items():
                    setattr(paper.analyses[0], field, value)
        session.commit()

        output_path = Path(__file__).resolve().parents[1] / "data" / "sample_data.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["title", "authors", "publication_year", "journal", "abstract", "topic", "citation_count", "source"])
            writer.writerows(
                [title, authors, year, journal, abstract, topic, citations, "Demo dataset — illustrative record"]
                for title, year, authors, topic, journal, citations, abstract in DEMO_PAPERS
            )
        return inserted
    finally:
        session.close()


if __name__ == "__main__":
    count = seed_database()
    print(f"Demo database ready. Added {count} papers; total sample records: {len(DEMO_PAPERS)}.")