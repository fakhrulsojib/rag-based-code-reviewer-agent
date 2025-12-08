"""Vector store wrapper for ChromaDB."""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.models import Chunk, RuleChunk
from src.config import settings
from src.logger import logger


class VectorStore:
    """Wrapper for ChromaDB vector store operations."""
    
    def __init__(self, collection_name: str = "code_rules"):
        """Initialize the vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Code review rules and guidelines"}
        )
        
        logger.info(f"Initialized vector store with collection: {collection_name}")
    
    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]):
        """Add chunks to the vector store.
        
        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings to add")
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Successfully added {len(chunks)} chunks")
    
    def upsert_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]):
        """Upsert (update or insert) chunks to the vector store.
        
        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings to upsert")
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        logger.info(f"Upserting {len(chunks)} chunks to vector store")
        
        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        
        # Upsert to collection
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Successfully upserted {len(chunks)} chunks")
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = None,
        where: Optional[Dict[str, Any]] = None
    ) -> List[RuleChunk]:
        """Query the vector store for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            where: Metadata filter (e.g., {"category": "java-entity"})
            
        Returns:
            List of RuleChunk objects with relevance scores
        """
        top_k = top_k or settings.top_k_rules
        
        logger.info(f"Querying vector store for top {top_k} results")
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )
        
        # Convert results to RuleChunk objects
        rule_chunks = []
        
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunk = Chunk(
                    chunk_id=results['ids'][0][i],
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    source_file=results['metadatas'][0][i].get('source_file', '')
                )
                
                # Distance to similarity score (ChromaDB uses L2 distance)
                distance = results['distances'][0][i]
                similarity = 1 / (1 + distance)  # Convert distance to similarity
                
                rule_chunk = RuleChunk(
                    chunk=chunk,
                    relevance_score=similarity
                )
                
                rule_chunks.append(rule_chunk)
        
        logger.info(f"Found {len(rule_chunks)} matching chunks")
        return rule_chunks
    
    def delete_by_source(self, source_file: str):
        """Delete all chunks from a specific source file.
        
        Args:
            source_file: Source file path
        """
        logger.info(f"Deleting chunks from source: {source_file}")
        
        # Query for chunks from this source
        results = self.collection.get(
            where={"source_file": source_file}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} chunks from {source_file}")
        else:
            logger.info(f"No chunks found for {source_file}")
    
    def clear(self):
        """Clear all data from the collection."""
        logger.warning("Clearing all data from vector store")
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Code review rules and guidelines"}
        )
        logger.info("Vector store cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        count = self.collection.count()
        
        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "persist_dir": settings.chroma_persist_dir
        }
