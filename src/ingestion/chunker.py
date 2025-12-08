"""Intelligent Markdown document chunker for rule files."""
import re
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from src.models import Chunk
from src.config import settings
from src.logger import logger


class MarkdownChunker:
    """Chunks Markdown documents intelligently based on structure."""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """Initialize the chunker.
        
        Args:
            chunk_size: Maximum chunk size in tokens (approximate)
            chunk_overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    def chunk_file(self, file_path: str) -> List[Chunk]:
        """Chunk a Markdown file into logical sections.
        
        Args:
            file_path: Path to the Markdown file
            
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.chunk_markdown(content, file_path)
    
    def chunk_markdown(self, content: str, source_file: str) -> List[Chunk]:
        """Chunk Markdown content into logical sections.
        
        Args:
            content: Markdown content
            source_file: Source file path
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        # Split by headers (## and ###)
        sections = self._split_by_headers(content)
        
        for section in sections:
            # Extract metadata from the section
            metadata = self._extract_metadata(section, source_file)
            
            # If section is too large, split it further
            if self._estimate_tokens(section['content']) > self.chunk_size:
                sub_chunks = self._split_large_section(section['content'])
                for i, sub_content in enumerate(sub_chunks):
                    chunk = self._create_chunk(
                        content=sub_content,
                        metadata=metadata,
                        source_file=source_file,
                        section_title=section['title'],
                        sub_index=i
                    )
                    chunks.append(chunk)
            else:
                chunk = self._create_chunk(
                    content=section['content'],
                    metadata=metadata,
                    source_file=source_file,
                    section_title=section['title']
                )
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {source_file}")
        return chunks
    
    def _split_by_headers(self, content: str) -> List[Dict[str, str]]:
        """Split content by Markdown headers.
        
        Args:
            content: Markdown content
            
        Returns:
            List of sections with title and content
        """
        sections = []
        
        # Pattern to match headers (## or ###)
        header_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
        
        matches = list(header_pattern.finditer(content))
        
        if not matches:
            # No headers found, treat entire content as one section
            return [{
                'title': Path(content[:50]).stem if content else 'root',
                'content': content,
                'level': 1
            }]
        
        for i, match in enumerate(matches):
            title = match.group(2).strip()
            level = len(match.group(1))
            start = match.end()
            
            # Find end of this section (next header or end of content)
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            section_content = content[start:end].strip()
            
            sections.append({
                'title': title,
                'content': section_content,
                'level': level
            })
        
        return sections
    
    def _split_large_section(self, content: str) -> List[str]:
        """Split a large section into smaller chunks with overlap.
        
        Args:
            content: Section content
            
        Returns:
            List of sub-chunks
        """
        # Split by paragraphs
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = self._estimate_tokens(para)
            
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_paras = self._get_overlap_paragraphs(current_chunk)
                current_chunk = overlap_paras + [para]
                current_size = sum(self._estimate_tokens(p) for p in current_chunk)
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _get_overlap_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Get paragraphs for overlap based on chunk_overlap setting.
        
        Args:
            paragraphs: List of paragraphs
            
        Returns:
            List of paragraphs for overlap
        """
        overlap_paras = []
        overlap_size = 0
        
        # Take paragraphs from the end until we reach overlap size
        for para in reversed(paragraphs):
            para_size = self._estimate_tokens(para)
            if overlap_size + para_size > self.chunk_overlap:
                break
            overlap_paras.insert(0, para)
            overlap_size += para_size
        
        return overlap_paras
    
    def _extract_metadata(self, section: Dict[str, str], source_file: str) -> Dict[str, Any]:
        """Extract metadata from a section.
        
        Args:
            section: Section dictionary
            source_file: Source file path
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'title': section['title'],
            'level': section['level'],
            'source_file': source_file
        }
        
        content = section['content']
        
        # Extract severity if present
        severity_match = re.search(r'\*\*Severity\*\*:\s*(High|Medium|Low)', content, re.IGNORECASE)
        if severity_match:
            metadata['severity'] = severity_match.group(1).capitalize()
        
        # Extract "Applies to" tags
        applies_to_match = re.search(r'\*\*Applies to\*\*:\s*(.+)', content, re.IGNORECASE)
        if applies_to_match:
            applies_to = applies_to_match.group(1)
            # Parse comma-separated values and convert to string
            tags = [tag.strip() for tag in applies_to.split(',')]
            metadata['applies_to'] = ', '.join(tags)  # Store as string for ChromaDB
        
        # Extract category from file name
        file_stem = Path(source_file).stem
        metadata['category'] = file_stem.replace('-rules', '').replace('_', '-')
        
        # Extract keywords from title and content
        keywords = self._extract_keywords(section['title'] + ' ' + content)
        metadata['keywords'] = ', '.join(keywords)  # Convert to string for ChromaDB
        
        return metadata
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Common technical keywords to look for
        keyword_patterns = [
            r'@\w+',  # Annotations like @Entity
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase words
            r'\bserialVersionUID\b',
            r'\bCREATE\s+TABLE\b',
            r'\bALTER\s+TABLE\b',
            r'\bsnake_case\b',
            r'\bcamelCase\b',
        ]
        
        keywords = set()
        for pattern in keyword_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.update(match.lower() for match in matches)
        
        return list(keywords)[:10]  # Limit to top 10
    
    def _create_chunk(
        self,
        content: str,
        metadata: Dict[str, Any],
        source_file: str,
        section_title: str,
        sub_index: int = None
    ) -> Chunk:
        """Create a Chunk object.
        
        Args:
            content: Chunk content
            metadata: Chunk metadata
            source_file: Source file path
            section_title: Section title
            sub_index: Sub-chunk index if split
            
        Returns:
            Chunk object
        """
        # Generate unique chunk ID
        chunk_id = self._generate_chunk_id(source_file, section_title, sub_index)
        
        return Chunk(
            content=content,
            metadata=metadata,
            chunk_id=chunk_id,
            source_file=source_file
        )
    
    def _generate_chunk_id(
        self,
        source_file: str,
        section_title: str,
        sub_index: int = None
    ) -> str:
        """Generate a unique chunk ID.
        
        Args:
            source_file: Source file path
            section_title: Section title
            sub_index: Sub-chunk index
            
        Returns:
            Unique chunk ID
        """
        # Create a hash from file path and section title
        content = f"{source_file}:{section_title}"
        if sub_index is not None:
            content += f":{sub_index}"
        
        hash_obj = hashlib.md5(content.encode())
        return hash_obj.hexdigest()[:12]
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        This is a rough approximation: ~4 characters per token.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
