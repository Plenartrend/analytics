import json

import pytest
from confluent_kafka import Producer, Consumer, KafkaException
import time

KAFKA_BROKER = "localhost:9092"
TOPIC = "queue"


@pytest.fixture(scope="module")
def producer():
    p = Producer({'bootstrap.servers': KAFKA_BROKER})
    yield p


@pytest.fixture(scope="module")
def consumer():
    c = Consumer({
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': 'test-group',
        'auto.offset.reset': 'earliest'
    })
    c.subscribe([TOPIC])
    yield c
    c.close()


@pytest.fixture(scope="module")
def mockdata():
    with open('../../data/speeches_no_block.json', 'r') as f:
        data = json.load(f)
        yield data


def test_kafka_message(producer, consumer):
    message = "Hello Kafka via Confluent!"

    # Produce message
    producer.produce(TOPIC, value=message)
    producer.flush(timeout=5)

    # Give Kafka some time to deliver
    time.sleep(1)

    # Consume message
    msg = consumer.poll(timeout=5.0)
    assert msg is not None, "No message received"
    if msg.error():
        raise KafkaException(msg.error())

    assert msg.value().decode("utf-8") == message


def test_send_document(producer, mockdata):
    document = {
        "event": "analyseEvent",
        "data": mockdata
    }

    producer.produce(TOPIC, value=json.dumps(document))
    producer.flush(timeout=5)

