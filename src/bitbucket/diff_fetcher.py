"""Bitbucket API client for fetching PR diffs."""
import httpx
from typing import List, Dict, Any
from src.models import FileDiff
from src.config import settings
from src.logger import logger


class DiffFetcher:
    """Fetches pull request diffs from Bitbucket API."""
    
    def __init__(self):
        """Initialize the diff fetcher."""
        self.base_url = "https://api.bitbucket.org/2.0"
        self.workspace = settings.bitbucket_workspace
        self.repo_slug = settings.bitbucket_repo_slug
        self.auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        logger.info(f"Initialized Bitbucket diff fetcher for {self.workspace}/{self.repo_slug}")
    
    async def fetch_pr_diff(self, pr_id: int) -> List[FileDiff]:
        """Fetch the diff for a pull request.
        
        Args:
            pr_id: Pull request ID
            
        Returns:
            List of FileDiff objects
        """
        logger.info(f"Fetching diff for PR #{pr_id}")
        
        # Fetch PR details
        pr_url = f"{self.base_url}/repositories/{self.workspace}/{self.repo_slug}/pullrequests/{pr_id}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Get PR metadata
            pr_response = await client.get(pr_url, auth=self.auth)
            pr_response.raise_for_status()
            pr_data = pr_response.json()
            
            # Get diff
            diff_url = f"{pr_url}/diff"
            diff_response = await client.get(diff_url, auth=self.auth)
            diff_response.raise_for_status()
            diff_content = diff_response.text
            
            # Get diffstat for file-level changes
            diffstat_url = f"{pr_url}/diffstat"
            diffstat_response = await client.get(diffstat_url, auth=self.auth)
            diffstat_response.raise_for_status()
            diffstat_data = diffstat_response.json()
        
        # Parse diff into FileDiff objects
        file_diffs = self._parse_diff(diff_content, diffstat_data)
        
        logger.info(f"Fetched {len(file_diffs)} file diffs for PR #{pr_id}")
        return file_diffs
    
    def _parse_diff(self, diff_content: str, diffstat_data: Dict[str, Any]) -> List[FileDiff]:
        """Parse unified diff into FileDiff objects.
        
        Args:
            diff_content: Unified diff content
            diffstat_data: Diffstat data from API
            
        Returns:
            List of FileDiff objects
        """
        file_diffs = []
        
        # Split diff by file
        file_sections = diff_content.split('diff --git')
        
        # Create a map of file paths to diffstat info
        diffstat_map = {}
        for item in diffstat_data.get('values', []):
            if 'new' in item and item['new']:
                file_path = item['new']['path']
                diffstat_map[file_path] = {
                    'additions': item.get('lines_added', 0),
                    'deletions': item.get('lines_removed', 0),
                    'status': item.get('status', 'modified')
                }
        
        for section in file_sections[1:]:  # Skip first empty split
            try:
                # Extract file path
                lines = section.split('\n')
                header = lines[0]
                
                # Parse file paths from header
                # Format: a/path/to/file b/path/to/file
                parts = header.split()
                if len(parts) >= 2:
                    file_path = parts[1].lstrip('b/')
                    
                    # Get diffstat info
                    stat_info = diffstat_map.get(file_path, {})
                    
                    # Determine change type
                    change_type = self._determine_change_type(section, stat_info.get('status', 'modified'))
                    
                    # Extract just the diff content (skip headers)
                    diff_lines = []
                    in_diff = False
                    for line in lines:
                        if line.startswith('@@'):
                            in_diff = True
                        if in_diff:
                            diff_lines.append(line)
                    
                    file_diff = FileDiff(
                        file_path=file_path,
                        diff_content='\n'.join(diff_lines),
                        change_type=change_type,
                        additions=stat_info.get('additions', 0),
                        deletions=stat_info.get('deletions', 0),
                        annotated_content=self._annotate_diff('\n'.join(diff_lines))
                    )
                    
                    file_diffs.append(file_diff)
            except Exception as e:
                logger.error(f"Error parsing diff section: {e}")
                continue
        
        return file_diffs

    def _annotate_diff(self, diff_content: str) -> str:
        """Annotate diff content with explicit line numbers.
        
        Args:
            diff_content: Raw diff content
            
        Returns:
            Annotated diff content with line numbers
        """
        annotated_lines = []
        current_line_number = 0
        
        for line in diff_content.split('\n'):
            # Parse chunk header
            if line.startswith('@@'):
                # Format: @@ -old_start,old_len +new_start,new_len @@
                try:
                    parts = line.split(' ')
                    new_file_part = parts[2] # +new_start,new_len
                    start_line = int(new_file_part.split(',')[0].replace('+', ''))
                    current_line_number = start_line
                    annotated_lines.append(line) # Keep header
                except Exception:
                    annotated_lines.append(line)
                continue
            
            # Handle diff lines
            if line.startswith('+'):
                annotated_lines.append(f"{current_line_number}: {line}")
                current_line_number += 1
            elif line.startswith(' '):
                annotated_lines.append(f"{current_line_number}: {line}")
                current_line_number += 1
            elif line.startswith('-'):
                # Deleted lines don't exist in the new file, so no line number
                annotated_lines.append(f"    {line}")
            else:
                annotated_lines.append(line)
                
        return '\n'.join(annotated_lines)
    
    def _determine_change_type(self, diff_section: str, status: str) -> str:
        """Determine the type of change from diff section.
        
        Args:
            diff_section: Diff section content
            status: Status from diffstat
            
        Returns:
            Change type: 'added', 'modified', or 'deleted'
        """
        if status == 'added' or 'new file mode' in diff_section:
            return 'added'
        elif status == 'removed' or 'deleted file mode' in diff_section:
            return 'deleted'
        else:
            return 'modified'
    
    async def get_pr_metadata(self, pr_id: int) -> Dict[str, Any]:
        """Get pull request metadata.
        
        Args:
            pr_id: Pull request ID
            
        Returns:
            PR metadata dictionary
        """
        pr_url = f"{self.base_url}/repositories/{self.workspace}/{self.repo_slug}/pullrequests/{pr_id}"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(pr_url, auth=self.auth)
            response.raise_for_status()
            return response.json()
