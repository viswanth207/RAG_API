from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
import logging
import os
from pinecone import Pinecone

logger = logging.getLogger(__name__)


class VectorStoreManager:
    
    def __init__(self):
        logger.info("Initializing HuggingFace embeddings...")
        
        # Prevent HuggingFace from hanging indefinitely on network checks if ISP blocks/throttles HF Hub
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if pinecone_api_key:
            self.pc = Pinecone(api_key=pinecone_api_key)
            self.index_name = "datamind"
        else:
            logger.warning("PINECONE_API_KEY is not set!")
        
        logger.info("Embeddings initialized successfully")
    
    def create_vector_store(self, documents: List[Document], namespace: str) -> PineconeVectorStore:
        if not documents:
            raise ValueError("Cannot create vector store with empty documents")
        
        try:
            # Clean metadata to prevent Pinecone 40KB limit errors
            documents = self._clean_metadata(documents)
            
            # CLEAR OLD VECTORS: Delete existing namespace to ensure a fresh, accurate index
            try:
                logger.info(f"Purging old vectors for namespace: {namespace}...")
                index = self.pc.Index(self.index_name)
                index.delete(delete_all=True, namespace=namespace)
            except Exception as e:
                logger.warning(f"Note: Could not purge namespace {namespace} (it might be new): {str(e)}")
            
            logger.info(f"Pushing {len(documents)} documents to Pinecone index 'datamind', namespace: {namespace}")
            
            vector_store = PineconeVectorStore.from_documents(
                documents=documents,
                embedding=self.embeddings,
                index_name=self.index_name,
                namespace=namespace
            )
            
            logger.info("Pinecone Vector store updated successfully")
            return vector_store
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise ValueError(f"Failed to create vector store: {str(e)}")
    
    def similarity_search(
        self, 
        vector_store: PineconeVectorStore, 
        query: str, 
        k: int = 4
    ) -> List[Document]:
        try:
            logger.info(f"Performing Pinecone similarity search for: {query[:50]}...")
            
            # 1. Extract potential exact-match keywords (numbers, dates, emails)
            import re
            keywords = []
            
            # Extract numbers/dates (e.g. 15, 29_3_2026, 2026-03-29, 1029)
            keywords.extend(re.findall(r'\b\d+(?:[_-]\d+)*\b', query))
            
            # Extract emails
            keywords.extend(re.findall(r'[\w\.-]+@[\w\.-]+', query))
            
            # Clean keywords
            keywords = [kw.lower() for kw in set(keywords) if len(kw) > 1 or len(keywords) == 1]
            
            if keywords:
                logger.info(f"Detected exact-match keywords for reranking: {keywords}")
                fetch_k = min(k * 3, 100) # Fetch up to 100 docs for deep keyword search
            else:
                fetch_k = k

            results = vector_store.similarity_search(
                query=query,
                k=fetch_k
            )
            
            # 2. Local Keyword Reranking
            if keywords and results:
                # We need a stable sort that keeps vector similarity as a tie-breaker.
                # Since results are already sorted by vector similarity (best first),
                # we assign them an initial score based on their position, then add massive boosts for keywords.
                scored_results = []
                for i, doc in enumerate(results):
                    content = doc.page_content.lower()
                    
                    # Base score is reversed index (e.g., if 75 docs, first doc gets 75, last gets 1)
                    score = len(results) - i
                    
                    for kw in keywords:
                        # Exact word boundary match for numbers to avoid matching '15' in '150'
                        if re.search(rf'\b{re.escape(kw)}\b', content):
                            score += 1000 # Massive boost
                            
                    scored_results.append((score, doc))
                
                # Sort by our custom score
                scored_results.sort(key=lambda x: x[0], reverse=True)
                results = [doc for score, doc in scored_results]
                
            # 3. Truncate back to k
            results = results[:k]
            
            logger.info(f"Found {len(results)} relevant documents in Pinecone after reranking")
            return results
            
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []
    
    def similarity_search_with_score(
        self, 
        vector_store: PineconeVectorStore, 
        query: str, 
        k: int = 4
    ) -> List[tuple[Document, float]]:
        try:
            logger.info(f"Performing Pinecone similarity search with scores for: {query[:50]}...")
            
            results = vector_store.similarity_search_with_score(
                query=query,
                k=k
            )
            
            logger.info(f"Found {len(results)} relevant documents with scores")
            return results
            
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []
    
    def load_vector_store(self, namespace: str) -> PineconeVectorStore:
        try:
            vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                namespace=namespace
            )
            logger.info(f"Connected to Pinecone index 'datamind', namespace: {namespace}")
            return vector_store
        except Exception as e:
            logger.error(f"Error loading Pinecone vector store: {str(e)}")
            raise

    def _clean_metadata(self, documents: List[Document]) -> List[Document]:
        """Ensure metadata doesn't exceed Pinecone's 40KB limit."""
        import json
        cleaned_docs = []
        for doc in documents:
            # CRITICAL: Pinecone stores the document text IN the metadata under 'text' key.
            # So total size = metadata_size + page_content_size
            meta_json_size = len(json.dumps(doc.metadata))
            content_size = len(doc.page_content)
            total_size = meta_json_size + content_size
            
            if total_size > 35000:  # 35KB safety limit
                logger.warning(f"Total Pinecone payload too large ({total_size} bytes). Aggressively pruning...")
                
                # 1. Truncate page content to 15k characters max
                if len(doc.page_content) > 15000:
                    doc.page_content = doc.page_content[:15000] + "...[TRUNCATED]"
                
                # 2. Keep only essential metadata fields
                essential_keys = {'_id', 'id', 'name', 'title', 'source', 'item_number', 'type'}
                new_metadata = {}
                for k, v in doc.metadata.items():
                    if k in essential_keys:
                        new_metadata[k] = v
                
                # 3. Only add other fields if they are tiny (under 200 chars)
                for k, v in doc.metadata.items():
                    if k not in essential_keys:
                        val_str = str(v)
                        if len(val_str) < 200:
                            new_metadata[k] = v
                            
                doc.metadata = new_metadata
                
            cleaned_docs.append(doc)
        return cleaned_docs

