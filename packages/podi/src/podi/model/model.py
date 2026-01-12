from pgvector.sqlalchemy import VECTOR
from sqlalchemy import TIMESTAMP, Column, DateTime, ForeignKey, Integer, Text, func, text
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
    "bundestag",
    "bundesrat",
    name="body",
    create_type=False,
)

DocumentTypeEnum = ENUM(
    "printedPaper",
    "protocol",
    name="document_type",
    create_type=False,
)


LatchTypeEnum = ENUM(
    "WORKING",
    "FINISHED",
    name="latch_type",
    create_type=True,
)


class ActivityLatch(Base):
    __tablename__ = "activity_latches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    latch = Column(
        LatchTypeEnum,
        server_default=text("'WORKING'"),
    )
    activity_id = Column(
        Integer,
        nullable=False,
    )
    hasharr_instance_id = Column(
        Integer,
        nullable=False,
    )
    created = Column(DateTime, server_default=func.now())
    updated = Column(DateTime)
    processed = Column(DateTime)


class Topic(Base):
    __table_args__ = {"schema": "plenartrend"}
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    embedding = Column(VECTOR(384))

    updated = Column(DateTime)
    created = Column(DateTime, server_default=func.now())


class ProcessTopic(Base):
    __table_args__ = {"schema": "plenartrend"}
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
    __table_args__ = {"schema": "plenartrend"}
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
    __table_args__ = {"schema": "plenartrend"}
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
