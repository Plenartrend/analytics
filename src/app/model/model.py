from pgvector.sqlalchemy import VECTOR
from sqlalchemy import TIMESTAMP, Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class HashrrInstance(Base):
    __tablename__ = "hashrr_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    heartbeats = relationship("HashrrHeartbeat", back_populates="instance", cascade="all, delete-orphan")


class HashrrHeartbeat(Base):
    __tablename__ = "hashrr_heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hashrr_instance_id = Column(Integer, ForeignKey("hashrr_instances.id", ondelete="CASCADE"), nullable=False)
    heartbeat = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    instance = relationship("HashrrInstance", back_populates="heartbeats")


BodyEnum = ENUM(
    "BT",
    "BR",
    name="body",
    create_type=False,
)

DocumentTypeEnum = ENUM(
    "printedPaper",
    "protocol",
    name="document_type",
    create_type=False,
)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    embedding = Column(VECTOR(384))

    updated = Column(DateTime)
    created = Column(DateTime, server_default=func.now())


class ProcessTopic(Base):
    __tablename__ = "process_topics"

    process_id = Column(
        Integer,
        nullable=False,
        primary_key=True,
    )
    topic_id = Column(
        Integer,
        ForeignKey("Topics.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    updated = Column(DateTime)
    created = Column(DateTime, server_default=func.now())


class PrintedPaper(Base):
    __tablename__ = "printed_papers"

    id = Column(Integer, primary_key=True)
    type = Column(Text)
    title = Column(Text, nullable=False)
    document_number = Column(Text, nullable=False)

    publisher = Column(BodyEnum)

    group_id = Column(Integer)
    url = Column(Text)
    text = Column(Text)

    election_period = Column(Integer)

    date = Column(DateTime)
    api_updated = Column(DateTime)
    updated = Column(DateTime)
    created = Column(DateTime, server_default=func.now())


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    type = Column(Text)

    role_id = Column(
        Integer,
        nullable=False,
    )

    document_type = Column(DocumentTypeEnum)

    printed_paper_id = Column(Integer)
    protocol_id = Column(Integer)

    text = Column(Text)

    api_updated = Column(DateTime)
    updated = Column(DateTime)
    created = Column(DateTime, server_default=func.now())


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(Text)
    title = Column(Text)
    name_suffix = Column(Text)

    last_name = Column(Text, nullable=False)
    first_name = Column(Text, nullable=False)

    person_id = Column(
        Integer,
        ForeignKey("plenartrend.persons.id", ondelete="CASCADE"),
        nullable=False,
    )

    group_id = Column(
        Integer,
        ForeignKey("plenartrend.parliamentary_groups.id"),
        nullable=True,
    )

    election_period = Column(
        Integer,
        ForeignKey("plenartrend.election_periods.id"),
        nullable=True,
    )

    updated = Column(DateTime)
    created = Column(DateTime)


class ActivityMapping(Base):
    __tablename__ = "activity_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(Integer, nullable=False)
    topic_id = Column(Integer, nullable=True)
    sentiment_value = Column(Float, nullable=True)
    sentiment_reason = Column(Text, nullable=True)


class ActivityTfidf(Base):
    __tablename__ = "activity_tfidf"

    person_id = Column(Integer, primary_key=True)
    tfidf_vector = Column(Text, nullable=False)


class ActivityRelevance(Base):
    __tablename__ = "activity_relevance"

    protocol_id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, primary_key=True)
    relevance = Column(Float, nullable=False)


class PrintedPaperMapping(Base):
    __tablename__ = "printed_paper_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    printed_paper_id = Column(Integer, nullable=False)
    topic_id = Column(Integer, nullable=True)
    sentiment_value = Column(Float, nullable=True)
    sentiment_reason = Column(Text, nullable=True)
