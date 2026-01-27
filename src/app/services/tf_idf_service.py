import datetime
import logging
import re

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import GermanStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import activity_repository as activity_repo

nltk.download("stopwords")

LOGGER = logging.getLogger(__name__)


async def calculate_tf_idf(person_id: int, date: datetime.datetime, session: AsyncSession):
    LOGGER.info("Calculating TF-IDF for person_id=%s after date=%s", person_id, date)

    activities = await activity_repo.get_activities_after(person_id, date, session)

    filtered_activities = []
    for activity in activities:
        if activity.text and len(activity.text.strip()) > 20:
            filtered_activities.append(activity)

    german_stopwords = set(stopwords.words("german"))
    stemmer = GermanStemmer()

    def tokenize(text):
        text = text.lower()
        words = re.findall(r"\b\w+\b", text)
        return [stemmer.stem(w) for w in words if w not in german_stopwords]

    documents = [activity.text for activity in activities if activity.text]

    try:
        vectorizer = TfidfVectorizer(tokenizer=tokenize, ngram_range=(1, 2), min_df=2, max_df=0.9)
        X = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()
    except ValueError:
        vectorizer = TfidfVectorizer(
            tokenizer=tokenize,
            ngram_range=(1, 2),
        )
        X = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()

    rows, cols = X.nonzero()

    tfidf_json = [{"doc_id": int(r), "term": terms[c], "tfidf": float(X[r, c])} for r, c in zip(rows, cols)]

    return tfidf_json
