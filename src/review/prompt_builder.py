"""Dynamic prompt builder for LLM code reviews."""
from typing import List
from src.models import RuleChunk, FileDiff
from src.logger import logger


class PromptBuilder:
    """Builds dynamic prompts for LLM code reviews."""
    
    SYSTEM_PROMPT = """You are a senior code reviewer with deep expertise in software engineering best practices.

Your role is to review code changes and provide constructive feedback based ONLY on the specific rules provided to you.

**Critical Constraints:**
1. Apply ONLY the rules explicitly provided in the context below
2. Do not invent or assume rules that are not provided
3. Be professional and concise - no lecturing or condescending tone
4. Focus on actionable feedback

**Severity Levels:**
- **High**: Critical issues that must be fixed (security, data integrity, breaking changes)
- **Medium**: Important issues that should be addressed (best practices, maintainability)
- **Low**: Suggestions for improvement (style, optimization, readability)

**Input Format:**
The code changes are provided in a unified diff format.
Each line of code is prefixed with its line number in the file (e.g., "10: +    some code").
Use these explicit line numbers for your findings.

**Output Format:**
Return a JSON array of findings. Each finding must have:
- file: relative file path
- line: line number (integer) from the provided diff
- code_snippet: the exact line of code identified (string)
- severity: "High", "Medium", or "Low"
- rule: brief description of the violated rule
- suggestion: specific, actionable suggestion for fixing the issue
- category: rule category (if available)

If no issues are found, return an empty array: []
"""
    
    def build_review_prompt(
        self,
        file_diffs: List[FileDiff],
        rule_chunks: List[RuleChunk]
    ) -> str:
        """Build a complete review prompt.
        
        Args:
            file_diffs: List of file diffs to review
            rule_chunks: Retrieved rule chunks
            
        Returns:
            Complete prompt string
        """
        logger.info(f"Building review prompt for {len(file_diffs)} files with {len(rule_chunks)} rules")
        
        # Build context section with rules
        context = self._build_context(rule_chunks)
        
        # Build input section with diffs
        input_section = self._build_input(file_diffs)
        
        # Combine into full prompt
        prompt = f"""{self.SYSTEM_PROMPT}

## Context: Applicable Rules

{context}

## Input: Code Changes to Review

{input_section}

## Task

Review the code changes above and identify any violations of the provided rules.
Return your findings as a JSON array following the specified format.
"""
        
        return prompt
    
    def _build_context(self, rule_chunks: List[RuleChunk]) -> str:
        """Build the context section with rules.
        
        Args:
            rule_chunks: Retrieved rule chunks
            
        Returns:
            Formatted context string
        """
        if not rule_chunks:
            return "No specific rules provided. Perform a general code review."
        
        context_parts = []
        
        for i, rule_chunk in enumerate(rule_chunks, 1):
            chunk = rule_chunk.chunk
            
            # Format rule chunk
            rule_section = f"### Rule {i}"
            
            # Add metadata if available
            if chunk.metadata.get('category'):
                rule_section += f" ({chunk.metadata['category']})"
            
            rule_section += "\n\n"
            
            # Add severity if available
            if chunk.metadata.get('severity'):
                rule_section += f"**Severity**: {chunk.metadata['severity']}\n\n"
            
            # Add applies_to if available
            if chunk.metadata.get('applies_to'):
                applies_to = ', '.join(chunk.metadata['applies_to'])
                rule_section += f"**Applies to**: {applies_to}\n\n"
            
            # Add rule content
            rule_section += chunk.content
            
            context_parts.append(rule_section)
        
        return "\n\n---\n\n".join(context_parts)
    
    def _build_input(self, file_diffs: List[FileDiff]) -> str:
        """Build the input section with file diffs.
        
        Args:
            file_diffs: List of file diffs
            
        Returns:
            Formatted input string
        """
        input_parts = []
        
        for file_diff in file_diffs:
            # Format file header
            file_section = f"### File: `{file_diff.file_path}`\n\n"
            file_section += f"**Change Type**: {file_diff.change_type}\n"
            file_section += f"**Additions**: +{file_diff.additions} | **Deletions**: -{file_diff.deletions}\n\n"
            
            # Add diff content
            file_section += "```diff\n"
            file_section += file_diff.annotated_content or file_diff.diff_content
            file_section += "\n```"
            
            input_parts.append(file_section)
        
        return "\n\n---\n\n".join(input_parts)
    
    def build_simple_prompt(self, question: str) -> str:
        """Build a simple prompt for testing.
        
        Args:
            question: Question to ask
            
        Returns:
            Prompt string
        """
        return f"{self.SYSTEM_PROMPT}\n\n{question}"
