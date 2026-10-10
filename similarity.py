import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

DATABASE = Path(__file__).parent / "research_database.db"
EMPTY = ["title", "category", "similarity_score"]


@lru_cache(maxsize=1)
def _load_index():
    """Build the TF-IDF index once per server process (not on every rerun)."""
    connection = sqlite3.connect(DATABASE)
    papers = pd.read_sql_query(
        "SELECT title, category, summary FROM papers WHERE title IS NOT NULL",
        connection,
    )
    connection.close()

    papers["summary"] = papers["summary"].fillna("")
    papers = papers.drop_duplicates(subset="title").reset_index(drop=True)

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform(papers["title"] + " " + papers["summary"])
    return papers, vectorizer, matrix


def _top_results(papers, scores, number_of_papers):
    order = scores.argsort()[::-1][:number_of_papers]
    return pd.DataFrame(
        {
            "title": papers["title"].iloc[order].values,
            "category": papers["category"].iloc[order].values,
            "similarity_score": (scores[order] * 100).round(2),
        }
    )


def find_similar_papers(paper_title, number_of_papers=5):
    papers, _, matrix = _load_index()

    matches = papers.index[papers["title"] == paper_title]
    if len(matches) == 0:
        return pd.DataFrame(columns=EMPTY)

    idx = matches[0]
    # Cosine similarity of ONE paper against all (TF-IDF rows are L2-normalised).
    # This avoids the old 10,000 x 10,000 matrix (~800 MB of RAM).
    scores = linear_kernel(matrix[idx], matrix).ravel()
    scores[idx] = -1  # exclude the paper itself

    return _top_results(papers, scores, number_of_papers)


def find_similar_to_new_paper(new_title, new_summary, top_n=5):
    text = f"{new_title or ''} {new_summary or ''}".strip()
    if not text:
        return pd.DataFrame(columns=EMPTY)

    papers, vectorizer, matrix = _load_index()
    scores = linear_kernel(vectorizer.transform([text]), matrix).ravel()

    return _top_results(papers, scores, top_n)
