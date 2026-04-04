from app.db.elasticsearch import elasticsearch_client
from loguru import logger

INDEX_NAME = "docuquery_chunks"
EMBEDDING_DIM = 768

def create_elasticsearch_index():
    if not elasticsearch_client:
        return

    if elasticsearch_client.indices.exists(index=INDEX_NAME):
        logger.info(f"Index {INDEX_NAME} already exists")
        return

    mapping = {
        "mappings": {
            "properties": {
                "document_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "text": {
                    "type": "text",
                    "analyzer": "english"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIM,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    elasticsearch_client.indices.create(index=INDEX_NAME, body=mapping)
    logger.info(f"Created Elasticsearch index: {INDEX_NAME}")

def index_chunks(chunks: list[dict], file_name: str, document_id: str, client):
    if not elasticsearch_client:
        logger.error("Elasticsearch not available, skipping indexing")
        return

    success_count = 0
    for chunk in chunks:
        try:
            embedding_result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=chunk["text"]
            )
            embedding = embedding_result.embeddings[0].values

            elasticsearch_client.index(
                index=INDEX_NAME,
                id=f"{document_id}-{chunk['index']}",
                document={
                    "document_id": document_id,
                    "source": file_name,
                    "chunk_index": chunk["index"],
                    "text": chunk["text"],
                    "embedding": embedding
                }
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to index chunk {chunk['index']}: {e}")

    elasticsearch_client.indices.refresh(index=INDEX_NAME)
    logger.info(f"Indexed {success_count}/{len(chunks)} chunks for {file_name}")

def hybrid_search(question: str, document_id: str, client, n: int = 5) -> list[str]:
    if not elasticsearch_client:
        logger.error("Elasticsearch not available")
        return []

    try:
        embedding_result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=question
        )
        query_embedding = embedding_result.embeddings[0].values

        # RRF query — combines BM25 + vector in one request
        response = elasticsearch_client.search(
            index=INDEX_NAME,
            body={
                "retriever": {
                    "rrf": {
                        "retrievers": [
                            {
                                # BM25 keyword search
                                "standard": {
                                    "query": {
                                        "bool": {
                                            "must": {
                                                "match": {
                                                    "text": question
                                                }
                                            },
                                            "filter": {
                                                "term": {
                                                    "document_id": document_id
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            {
                                # vector similarity search
                                "knn": {
                                    "field": "embedding",
                                    "query_vector": query_embedding,
                                    "num_candidates": 50,
                                    "filter": {
                                        "term": {
                                            "document_id": document_id
                                        }
                                    }
                                }
                            }
                        ],
                        # k value in RRF formula
                        "rank_constant": 60,    
                        # candidates per retriever
                        "window_size": 100      
                    }
                },
                "size": n
            }
        )

        chunks = [hit["_source"]["text"] for hit in response["hits"]["hits"]]
        logger.info(f"Hybrid search returned {len(chunks)} chunks for: {question[:50]}")
        return chunks

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        return []