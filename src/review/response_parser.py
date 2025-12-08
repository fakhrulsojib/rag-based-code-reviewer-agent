"""Response parser for LLM review outputs."""
import json
import re
from typing import List
from src.models import Finding
from src.logger import logger


class ResponseParser:
    """Parses and validates LLM review responses."""
    
    def parse_findings(self, response: str) -> List[Finding]:
        """Parse LLM response into Finding objects.
        
        Args:
            response: LLM response text
            
        Returns:
            List of Finding objects
        """
        logger.info("Parsing LLM response")
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        
        if not json_str:
            logger.warning("No JSON found in response")
            return []
        
        try:
            # Parse JSON
            findings_data = json.loads(json_str)
            
            if not isinstance(findings_data, list):
                logger.error("Response is not a JSON array")
                return []
            
            # Convert to Finding objects
            findings = []
            for item in findings_data:
                try:
                    finding = Finding(**item)
                    findings.append(finding)
                except Exception as e:
                    logger.error(f"Error parsing finding: {e}, data: {item}")
                    continue
            
            logger.info(f"Parsed {len(findings)} findings from response")
            return findings
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            return []
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON array from text.
        
        Args:
            text: Text containing JSON
            
        Returns:
            JSON string or empty string if not found
        """
        # Try to find JSON array in markdown code blocks
        code_block_pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        
        if match:
            return match.group(1)
        
        # Try to find JSON array directly
        array_pattern = r'\[\s*\{.*?\}\s*\]'
        match = re.search(array_pattern, text, re.DOTALL)
        
        if match:
            return match.group(0)
        
        # Try to find empty array
        if '[]' in text:
            return '[]'
        
        return ''
    
    def validate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Validate and filter findings.
        
        Args:
            findings: List of Finding objects
            
        Returns:
            Validated list of findings
        """
        validated = []
        
        for finding in findings:
            # Check required fields
            if not finding.file or not finding.rule or not finding.suggestion:
                logger.warning(f"Skipping invalid finding: {finding}")
                continue
            
            # Check severity
            if finding.severity not in ['High', 'Medium', 'Low']:
                logger.warning(f"Invalid severity '{finding.severity}', defaulting to Medium")
                finding.severity = 'Medium'
            
            validated.append(finding)
        
        logger.info(f"Validated {len(validated)}/{len(findings)} findings")
        return validated
