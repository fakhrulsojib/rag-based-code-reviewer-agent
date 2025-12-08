"""Smart retrieval engine for fetching relevant rules."""
from typing import List
from src.models import RuleChunk
from src.ingestion.embedder import Embedder
from src.ingestion.vector_store import VectorStore
from src.retrieval.query_builder import QueryBuilder
from src.config import settings
from src.logger import logger


class Retriever:
    """Retrieves relevant rules from the vector store based on anchors."""
    
    def __init__(self):
        """Initialize the retriever."""
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.query_builder = QueryBuilder()
        logger.info("Initialized retriever")
    
    async def retrieve_rules(
        self,
        anchor_tags: List[str],
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[RuleChunk]:
        """Retrieve relevant rules based on anchor tags.
        
        Args:
            anchor_tags: List of anchor tags from detection
            top_k: Number of rules to retrieve
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of RuleChunk objects with relevance scores
        """
        top_k = top_k or settings.top_k_rules
        similarity_threshold = similarity_threshold or settings.similarity_threshold
        
        logger.info(f"Retrieving rules for anchors: {anchor_tags}")
        
        # Build semantic query
        query = self.query_builder.build_query(anchor_tags)
        
        # Generate query embedding
        query_embedding = await self.embedder.embed_query(query)
        
        # Build metadata filter (optional)
        metadata_filter = self.query_builder.build_metadata_filter(anchor_tags)
        
        # Query vector store
        rule_chunks = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more results for filtering
            where=metadata_filter if metadata_filter else None
        )
        
        # Filter by similarity threshold
        filtered_chunks = [
            chunk for chunk in rule_chunks
            if chunk.relevance_score >= similarity_threshold
        ]
        
        # Deduplicate based on content similarity
        deduplicated = self._deduplicate_chunks(filtered_chunks)
        
        # Limit to top_k
        final_chunks = deduplicated[:top_k]
        
        logger.info(f"Retrieved {len(final_chunks)} relevant rules")
        for i, chunk in enumerate(final_chunks, 1):
            # Use source or id as title might not exist
            title = chunk.chunk.metadata.get('source', chunk.chunk.chunk_id)
            logger.info(f"  Rule {i}: {title} (score: {chunk.relevance_score:.3f}, category: {chunk.chunk.metadata.get('category', 'N/A')})")
            logger.debug(f"    Content preview: {chunk.chunk.content[:100]}...")
        
        return final_chunks
    
    def _deduplicate_chunks(self, chunks: List[RuleChunk]) -> List[RuleChunk]:
        """Remove duplicate or highly similar chunks.
        
        Args:
            chunks: List of RuleChunk objects
            
        Returns:
            Deduplicated list
        """
        if not chunks:
            return []
        
        # Simple deduplication based on chunk_id
        seen_ids = set()
        deduplicated = []
        
        for chunk in chunks:
            if chunk.chunk.chunk_id not in seen_ids:
                deduplicated.append(chunk)
                seen_ids.add(chunk.chunk.chunk_id)
        
        logger.info(f"Deduplicated {len(chunks)} chunks to {len(deduplicated)}")
        return deduplicated
    
    def expand_related_rules(
        self,
        anchor_tags: List[str],
        initial_chunks: List[RuleChunk],
        expansion_factor: int = 2
    ) -> List[RuleChunk]:
        """Expand retrieval to include related rules.
        
        This helps catch rules that might be indirectly related.
        
        Args:
            anchor_tags: Original anchor tags
            initial_chunks: Initially retrieved chunks
            expansion_factor: How many more chunks to retrieve
            
        Returns:
            Expanded list of RuleChunk objects
        """
        logger.info(f"Expanding retrieval with factor {expansion_factor}")
        
        # Get additional chunks with lower threshold
        additional_chunks = self.retrieve_rules(
            anchor_tags=anchor_tags,
            top_k=expansion_factor,
            similarity_threshold=settings.similarity_threshold * 0.8
        )
        
        # Combine and deduplicate
        all_chunks = initial_chunks + additional_chunks
        deduplicated = self._deduplicate_chunks(all_chunks)
        
        return deduplicated
