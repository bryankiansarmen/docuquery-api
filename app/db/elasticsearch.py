from elasticsearch import Elasticsearch
from loguru import logger
import os

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")

elasticsearch_client = None

try:
    elasticsearch_client = Elasticsearch(
        ELASTICSEARCH_URL
    )
    if elasticsearch_client.ping():
        logger.info(f"Connected to Elasticsearch at {ELASTICSEARCH_URL}")
    else:
        logger.error("Elasticsearch ping failed")
        elasticsearch_client = None
except Exception as e:
    logger.error(f"Failed to connect to Elasticsearch: {e}")