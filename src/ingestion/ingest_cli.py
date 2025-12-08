"""CLI tool for ingesting rule files into the vector store."""
import argparse
from pathlib import Path
from typing import List
from src.ingestion.chunker import MarkdownChunker
from src.ingestion.embedder import Embedder
from src.ingestion.vector_store import VectorStore
from src.models import Chunk
from src.logger import logger
from src.config import settings


class IngestionEngine:
    """Orchestrates the ingestion of rule files into the vector store."""
    
    def __init__(self):
        """Initialize the ingestion engine."""
        self.chunker = MarkdownChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        logger.info("Initialized ingestion engine")
    
    def ingest_directory(self, rules_dir: str, rebuild: bool = False):
        """Ingest all Markdown files from a directory.
        
        Args:
            rules_dir: Directory containing rule files
            rebuild: If True, clear existing data before ingesting
        """
        rules_path = Path(rules_dir)
        
        if not rules_path.exists():
            logger.error(f"Rules directory not found: {rules_dir}")
            return
        
        # Clear existing data if rebuild requested
        if rebuild:
            logger.info("Rebuild requested, clearing vector store")
            self.vector_store.clear()
        
        # Find all Markdown files
        md_files = list(rules_path.glob("**/*.md"))
        
        if not md_files:
            logger.warning(f"No Markdown files found in {rules_dir}")
            return
        
        logger.info(f"Found {len(md_files)} Markdown files to ingest")
        
        # Process each file
        total_chunks = 0
        for md_file in md_files:
            try:
                chunks_added = self.ingest_file(str(md_file))
                total_chunks += chunks_added
            except Exception as e:
                logger.error(f"Error ingesting {md_file}: {e}")
        
        logger.info(f"Ingestion complete. Total chunks added: {total_chunks}")
        
        # Print statistics
        stats = self.vector_store.get_stats()
        logger.info(f"Vector store stats: {stats}")
    
    def ingest_file(self, file_path: str) -> int:
        """Ingest a single rule file.
        
        Args:
            file_path: Path to the rule file
            
        Returns:
            Number of chunks added
        """
        logger.info(f"Ingesting file: {file_path}")
        
        # Chunk the file
        chunks = self.chunker.chunk_file(file_path)
        
        if not chunks:
            logger.warning(f"No chunks created from {file_path}")
            return 0
        
        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)
        
        # Add to vector store
        self.vector_store.upsert_chunks(chunks, embeddings)
        
        logger.info(f"Added {len(chunks)} chunks from {file_path}")
        return len(chunks)
    
    def update_file(self, file_path: str):
        """Update an existing rule file in the vector store.
        
        Args:
            file_path: Path to the rule file
        """
        logger.info(f"Updating file: {file_path}")
        
        # Delete existing chunks from this file
        self.vector_store.delete_by_source(file_path)
        
        # Re-ingest the file
        self.ingest_file(file_path)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest code review rules into vector store"
    )
    parser.add_argument(
        "--rules-dir",
        type=str,
        default=settings.rules_dir,
        help="Directory containing rule files"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear existing data before ingesting"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Ingest a single file instead of directory"
    )
    
    args = parser.parse_args()
    
    engine = IngestionEngine()
    
    if args.file:
        # Ingest single file
        engine.ingest_file(args.file)
    else:
        # Ingest directory
        engine.ingest_directory(args.rules_dir, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
