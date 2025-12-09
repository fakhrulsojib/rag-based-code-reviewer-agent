"""Bitbucket API client for posting review comments."""
import httpx
from typing import List
from src.models import Finding
from src.config import settings
from src.logger import logger


class CommentPoster:
    """Posts review comments to Bitbucket pull requests."""
    
    def __init__(self):
        """Initialize the comment poster."""
        self.base_url = "https://api.bitbucket.org/2.0"
        self.workspace = settings.bitbucket_workspace
        self.repo_slug = settings.bitbucket_repo_slug
        self.auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        logger.info(f"Initialized Bitbucket comment poster for {self.workspace}/{self.repo_slug}")
    
    async def post_findings(self, pr_id: int, findings: List[Finding]) -> int:
        """Post review findings as inline comments.
        
        Args:
            pr_id: Pull request ID
            findings: List of Finding objects
            
        Returns:
            Number of comments posted
        """
        logger.info(f"Posting {len(findings)} findings to PR #{pr_id}")
        
        posted_count = 0
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for finding in findings:
                try:
                    logger.info(f"Posting comment for {finding.file}:{finding.line} - {finding.severity}")
                    await self._post_inline_comment(client, pr_id, finding)
                    posted_count += 1
                except Exception as e:
                    logger.error(f"Failed to post comment for {finding.file}:{finding.line}: {e}")
        
        logger.info(f"Posted {posted_count}/{len(findings)} inline comments")
        
        return posted_count
    
    async def _post_inline_comment(
        self,
        client: httpx.AsyncClient,
        pr_id: int,
        finding: Finding
    ) -> None:
        """Post an inline comment on a specific line.
        
        Args:
            client: HTTP client
            pr_id: Pull request ID
            finding: Code review finding
        """
        # Simplified comment format: just the suggestion
        comment_text = finding.suggestion
        
        # Bitbucket API endpoint for inline comments
        comment_url = f"{self.base_url}/repositories/{self.workspace}/{self.repo_slug}/pullrequests/{pr_id}/comments"
        
        payload = {
            "content": {
                "raw": comment_text
            },
            "inline": {
                "to": finding.line,
                "path": finding.file
            }
        }
        
        logger.debug(f"Comment payload: {payload}")
        
        response = await client.post(
            comment_url,
            json=payload,
            auth=self.auth
        )
        
        if response.status_code not in [200, 201]:
            logger.error(f"Failed to post comment: {response.status_code} - {response.text}")
            response.raise_for_status()
        else:
            logger.info(f"Successfully posted comment on {finding.file}:{finding.line}")
        
        logger.debug(f"Posted comment for {finding.file}:{finding.line}")
    
    def _format_comment(self, finding: Finding) -> str:
        """Format a finding as a comment.
        
        Args:
            finding: Finding object
            
        Returns:
            Formatted comment string
        """
        return finding.suggestion
    

