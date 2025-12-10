"""Module for reporting review artifacts."""
import os
import json
from datetime import datetime
from typing import List, Any, Dict
from src.models import FileDiff, Anchor, RuleChunk, Finding
from src.logger import logger

class ReviewReporter:
    """Handles saving review artifacts to the file system."""
    
    def __init__(self, base_dir: str = "reports"):
        """Initialize reporter.
        
        Args:
            base_dir: Base directory for reports
        """
        self.base_dir = base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

    def create_report_dir(self, pr_id: int) -> str:
        """Create a directory for the current review run.
        
        Args:
            pr_id: Pull Request ID
            
        Returns:
            Path to the created directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{timestamp}_{pr_id}"
        report_path = os.path.join(self.base_dir, dir_name)
        
        if not os.path.exists(report_path):
            os.makedirs(report_path)
            logger.info(f"Created report directory: {report_path}")
            
        return report_path
    
    def _get_chunk_dir(self, report_dir: str, chunk_id: int) -> str:
        """Get or create chunk subdirectory.
        
        Args:
            report_dir: Path to report directory
            chunk_id: Chunk index
            
        Returns:
            Path to chunk directory
        """
        chunk_path = os.path.join(report_dir, f"chunk_{chunk_id}")
        if not os.path.exists(chunk_path):
            os.makedirs(chunk_path)
        return chunk_path

    def save_chunk_data(self, report_dir: str, chunk_id: int, file_diffs: List[FileDiff]):
        """Save diff data for a chunk.
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            file_diffs: List of FileDiff objects
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "diffs.json")
        
        data = [diff.dict() for diff in file_diffs]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_anchors(self, report_dir: str, chunk_id: int, anchors: List[Anchor]):
        """Save detected anchors.
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            anchors: List of Anchor objects
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "anchors.json")
        
        data = [anchor.dict() for anchor in anchors]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_rules(self, report_dir: str, chunk_id: int, rules: List[RuleChunk]):
        """Save retrieved rules.
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            rules: List of RuleChunk objects
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "rules.json")
        
        data = [rule.dict() for rule in rules]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_prompt(self, report_dir: str, chunk_id: int, prompt: str):
        """Save constructed prompt.
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            prompt: Prompt string
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "prompt.txt")
        
        with open(file_path, 'w') as f:
            f.write(prompt)

    def save_response(self, report_dir: str, chunk_id: int, raw_response: str, parsed_findings: List[Finding]):
        """Save LLM response (raw and parsed).
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            raw_response: Raw LLM output
            parsed_findings: List of Finding objects
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        
        # Save raw response
        with open(os.path.join(path, "raw_response.txt"), 'w') as f:
            f.write(raw_response)
            
        # Save parsed findings
        data = [finding.dict() for finding in parsed_findings]
        with open(os.path.join(path, "parsed_response.json"), 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def save_comments(self, report_dir: str, chunk_id: int, findings: List[Finding]):
        """Save comments that were posted (or would be posted).
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            findings: List of Finding objects (verified)
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "posted_comments.json")
        
        data = [finding.dict() for finding in findings]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_possible_comments(self, report_dir: str, chunk_id: int, findings: List[Finding]):
        """Save potential comments for manual review.
        
        Args:
            report_dir: Report directory path
            chunk_id: Chunk index
            findings: List of Finding objects (verified)
        """
        path = self._get_chunk_dir(report_dir, chunk_id)
        file_path = os.path.join(path, "possible_comments.json")
        
        data = [finding.dict() for finding in findings]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_status(self, report_dir: str, status_data: Dict[str, Any]):
        """Save status of the review process.
        
        Args:
            report_dir: Report directory path
            status_data: Dictionary containing status info
        """
        file_path = os.path.join(report_dir, "status.json")
        with open(file_path, 'w') as f:
            json.dump(status_data, f, indent=2, default=str)
