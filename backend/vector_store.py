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
            
            results = vector_store.similarity_search(
                query=query,
                k=k
            )
            
            logger.info(f"Found {len(results)} relevant documents in Pinecone")
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
