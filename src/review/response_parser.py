"""Response parser for LLM review outputs."""
import json
import re
from typing import List
from src.models import Finding
from src.logger import logger
import json_repair


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
        
        try:
            # Clean JSON before parsing using regex to handle unescaped quotes
            cleaned_response = self._clean_json(response)
            
            # Use json_repair to parse and fix JSON from the response
            # return_objects=True returns the parsed object instead of a string
            findings_data = json_repair.repair_json(cleaned_response, return_objects=True)
            
            # If nothing was parsed or it returned None
            if not findings_data:
                logger.warning("No JSON found or parsed from response")
                return []
            
            # Handle case where it might parse a single dictionary instead of a list
            if isinstance(findings_data, dict):
                findings_data = [findings_data]
            
            if not isinstance(findings_data, list):
                logger.error(f"Parsed data is not a list: {type(findings_data)}")
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
            
        except Exception as e:
            logger.error(f"Error parsing/repairing JSON: {e}")
            return []
    
    def _clean_json(self, text: str) -> str:
        """Clean JSON string by fixing common LLM formatting issues.
        
        Args:
            text: Raw JSON string
            
        Returns:
            Cleaned JSON string
        """
        # Pattern to find code_snippet value and the following severity field
        # We look for "code_snippet": " ... ", "severity"
        # capturing the content inside the quotes.
        pattern = r'("code_snippet"\s*:\s*")(.*?)("\s*,\s*"severity")'
        
        def replace_match(match):
            prefix = match.group(0)
            start_quote = match.group(1)
            content = match.group(2)
            end_suffix = match.group(3)
            
            # Escape quotes inside content that aren't already escaped
            # Using regex lookbehind to find " not preceded by \
            cleaned_content = re.sub(r'(?<!\\)"', r'\\"', content)
            
            # Escape newlines
            cleaned_content = cleaned_content.replace('\n', '\\n')
            
            return f'{start_quote}{cleaned_content}{end_suffix}'

        # Apply replacement
        try:
            return re.sub(pattern, replace_match, text, flags=re.DOTALL)
        except Exception as e:
            logger.warning(f"Error extracting/cleaning code snippets: {e}")
            return text
    
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
