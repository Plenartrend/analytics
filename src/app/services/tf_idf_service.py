import datetime
import logging

import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import activity_repository as activity_repo

nlp = spacy.load("de_core_news_sm")

LOGGER = logging.getLogger(__name__)


async def calculate_tf_idf(person_id: int, date: datetime.datetime, session: AsyncSession):
    LOGGER.info("Calculating TF-IDF for person_id=%s after date=%s", person_id, date)

    activities = await activity_repo.get_activities(person_id, date, session)

    filtered_activities = []
    for activity in activities:
        if activity.text and len(activity.text.strip()) > 20:
            filtered_activities.append(activity)

    def tokenize(text):
        doc = nlp(text.lower())
        return [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]

    documents = [activity.text for activity in filtered_activities if activity.text]

    if not documents:
        return []

    try:
        vectorizer = TfidfVectorizer(tokenizer=tokenize, min_df=2, max_df=0.9)
        X = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()
    except ValueError:
        vectorizer = TfidfVectorizer(tokenizer=tokenize)
        X = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()

    rows, cols = X.nonzero()

    tfidf_json = [{"doc_id": int(r), "term": terms[c], "tfidf": float(X[r, c])} for r, c in zip(rows, cols)]

    return tfidf_json
