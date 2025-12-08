"""Manual review handler for on-demand PR reviews."""
from src.models import ReviewRequest
from src.logger import logger


class ManualReviewHandler:
    """Handles manual PR review requests."""
    
    def __init__(self):
        """Initialize the manual review handler."""
        logger.info("Initialized manual review handler")
    
    def validate_request(self, request: ReviewRequest) -> bool:
        """Validate a manual review request.
        
        Args:
            request: ReviewRequest object
            
        Returns:
            True if valid
        """
        if request.pr_id <= 0:
            logger.error(f"Invalid PR ID: {request.pr_id}")
            return False
        
        logger.info(f"Validated manual review request for PR #{request.pr_id}")
        return True
    
    def should_force_refresh(self, request: ReviewRequest) -> bool:
        """Check if review should be forced to refresh.
        
        Args:
            request: ReviewRequest object
            
        Returns:
            True if should force refresh
        """
        return request.force_refresh
