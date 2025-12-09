"""Embedding generation using Google Gemini."""
from typing import List
import google.generativeai as genai
from src.config import settings
from src.logger import logger


class Embedder:
    """Generate embeddings for text using configured provider."""
    
    def __init__(self):
        """Initialize the embedder with the configured provider."""
        self.provider = settings.embedding_provider
        
        if self.provider == "ollama":
            from langchain_ollama import OllamaEmbeddings
            self.model = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model
            )
            logger.info(f"Initialized Ollama embedder with model: {settings.ollama_embedding_model}")
        else:
            # Default to Gemini
            genai.configure(api_key=settings.gemini_api_key)
            self.model_name = settings.embedding_model # Keep this for Gemini's direct calls
            self.model = None  # Use direct API calls for Gemini
            logger.info(f"Initialized Gemini embedder with model: {settings.embedding_model}")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        embeddings: List[List[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                if self.provider == "ollama":
                    # OllamaEmbeddings provides embed_documents directly
                    batch_embeddings = self.model.embed_documents(batch)
                else:
                    batch_embeddings = self._embed_batch(batch)
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i}: {e}")
                embeddings.extend([[0.0] * 768 for _ in batch])
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else [0.0] * 768
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents.
        
        Args:
            texts: List of text documents
            
        Returns:
            List of embedding vectors
        """
        if self.provider == "ollama":
            try:
                # Ollama embeddings (synchronous)
                embeddings = self.model.embed_documents(texts)
                logger.info(f"Generated {len(embeddings)} embeddings via Ollama")
                return embeddings
            except Exception as e:
                logger.error(f"Error embedding documents with Ollama: {e}")
                # Return zero vectors as fallback
                return [[0.0] * 768 for _ in texts]
        else:
            # Gemini embeddings
            embeddings = []
            for i, text in enumerate(texts):
                try:
                    result = genai.embed_content(
                        model=settings.embedding_model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f"Error embedding text: {e}")
                    embeddings.append([0.0] * 768)
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using Gemini API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            except Exception as e:
                logger.error(f"Error embedding text: {e}")
                # Return zero vector for failed embedding
                embeddings.append([0.0] * 768)
        
        return embeddings
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query.
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector
        """
        if self.provider == "ollama":
            try:
                # Ollama query embedding (synchronous)
                embedding = self.model.embed_query(text)
                return embedding
            except Exception as e:
                logger.error(f"Error embedding query with Ollama: {e}")
                return [0.0] * 768
        else:
            # Gemini query embedding
            try:
                result = genai.embed_content(
                    model=settings.embedding_model,
                    content=text,
                    task_type="retrieval_query"
                )
                return result['embedding']
            except Exception as e:
                logger.error(f"Error embedding query: {e}")
                return [0.0] * 768
