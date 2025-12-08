"""Bitbucket API client for fetching raw file content."""
import httpx
from src.config import settings
from src.logger import logger


class FileFetcher:
    """Fetches raw file content from Bitbucket API."""
    
    def __init__(self):
        """Initialize the file fetcher."""
        self.base_url = "https://api.bitbucket.org/2.0"
        self.workspace = settings.bitbucket_workspace
        self.repo_slug = settings.bitbucket_repo_slug
        self.auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        logger.info(f"Initialized Bitbucket file fetcher for {self.workspace}/{self.repo_slug}")
    
    async def fetch_file_content(self, file_path: str, commit_hash: str) -> str:
        """Fetch raw content of a file at a specific commit.
        
        Args:
            file_path: Path to the file
            commit_hash: Commit hash or branch name
            
        Returns:
            Raw file content as string
        """
        # API endpoint: /repositories/{workspace}/{repo_slug}/src/{commit}/{path}
        url = f"{self.base_url}/repositories/{self.workspace}/{self.repo_slug}/src/{commit_hash}/{file_path}"
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, auth=self.auth)
                response.raise_for_status()
                return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching file {file_path} at {commit_hash}: {e.response.status_code}")
            return ""
        except Exception as e:
            logger.error(f"Error fetching file {file_path}: {e}")
            return ""
