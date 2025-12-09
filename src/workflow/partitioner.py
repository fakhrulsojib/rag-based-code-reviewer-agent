"""Module for partitioning diffs into manageable chunks."""
from typing import List
from src.models import FileDiff
from src.logger import logger

class DiffPartitioner:
    """Partitions file diffs into chunks based on line count."""
    
    def __init__(self, max_lines: int = 2000):
        """Initialize partitioner.
        
        Args:
            max_lines: Maximum number of lines per chunk (default 200)
        """
        self.max_lines = max_lines

    def partition_diffs(self, file_diffs: List[FileDiff]) -> List[List[FileDiff]]:
        """Partition file diffs into chunks.
        
        Rules:
        1. In each partition, will allow at max 200 lines of code.
        2. Will not partition in between a single file. (Unless file > 200 lines, then it's a single chunk)
        3. If a file line crosses 200 itself, it will have more than 200 lines in a single chunk, containing only itself.
        4. If a chunk already have lets say x line and taking a new file will cross 200 line (x + new lines > 200),
           then this file will not be added in the chunk. It will start a new chunk.
        
        Args:
            file_diffs: List of FileDiff objects
            
        Returns:
            List of chunks, where each chunk is a list of FileDiff objects
        """
        chunks: List[List[FileDiff]] = []
        current_chunk: List[FileDiff] = []
        current_chunk_lines = 0
        
        for file_diff in file_diffs:
            # Calculate lines in this file diff
            # We use diff_content line count as the metric
            # Note: diff_content represents the uni-diff including context
            file_lines = len(file_diff.diff_content.splitlines())
            
            # Case 1: File itself exceeds limit
            if file_lines > self.max_lines:
                # If we have a current chunk accumulating, finalize it first
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_chunk_lines = 0
                
                # Add this large file as its own chunk
                chunks.append([file_diff])
                logger.info(f"File {file_diff.file_path} ({file_lines} lines) exceeds limit, created standalone chunk.")
                continue
            
            # Case 2: Adding this file would exceed limit
            if current_chunk_lines + file_lines > self.max_lines:
                # Finalize current chunk
                chunks.append(current_chunk)
                
                # Start new chunk with this file
                current_chunk = [file_diff]
                current_chunk_lines = file_lines
            else:
                # Case 3: Fits in current chunk
                current_chunk.append(file_diff)
                current_chunk_lines += file_lines
        
        # Add remaining chunk if exists
        if current_chunk:
            chunks.append(current_chunk)
            
        logger.info(f"Partitioned {len(file_diffs)} files into {len(chunks)} chunks.")
        return chunks
