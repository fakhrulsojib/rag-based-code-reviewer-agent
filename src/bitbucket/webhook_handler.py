"""Webhook handler for Bitbucket events."""
import hmac
import hashlib
from fastapi import Request, HTTPException
from src.models import PREvent
from src.config import settings
from src.logger import logger
from datetime import datetime


class WebhookHandler:
    """Handles Bitbucket webhook events."""
    
    def __init__(self):
        """Initialize the webhook handler."""
        self.webhook_secret = settings.bitbucket_webhook_secret
        logger.info("Initialized webhook handler")
    
    async def validate_webhook(self, request: Request) -> bool:
        """Validate webhook signature.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if valid, raises HTTPException if invalid
        """
        # Get signature from headers
        signature = request.headers.get('X-Hub-Signature')
        
        if not signature:
            logger.warning("Webhook request missing signature")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # Get request body
        body = await request.body()
        
        # Calculate expected signature
        expected_signature = self._calculate_signature(body)
        
        # Compare signatures
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        logger.debug("Webhook signature validated")
        return True
    
    def _calculate_signature(self, body: bytes) -> str:
        """Calculate HMAC signature for webhook payload.
        
        Args:
            body: Request body bytes
            
        Returns:
            Signature string
        """
        mac = hmac.new(
            self.webhook_secret.encode(),
            msg=body,
            digestmod=hashlib.sha256
        )
        return f"sha256={mac.hexdigest()}"
    
    async def parse_pr_event(self, request: Request) -> PREvent:
        """Parse pull request event from webhook payload.
        
        Args:
            request: FastAPI request object
            
        Returns:
            PREvent object
        """
        payload = await request.json()
        
        # Extract event type
        event_key = request.headers.get('X-Event-Key', '')
        
        # Map event key to our event type
        event_type = self._map_event_type(event_key)
        
        # Extract PR data
        pr_data = payload.get('pullrequest', {})
        
        if not pr_data:
            logger.error("No pullrequest data in webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        
        # Create PREvent
        pr_event = PREvent(
            pr_id=pr_data.get('id'),
            title=pr_data.get('title', ''),
            source_branch=pr_data.get('source', {}).get('branch', {}).get('name', ''),
            destination_branch=pr_data.get('destination', {}).get('branch', {}).get('name', ''),
            author=pr_data.get('author', {}).get('username', ''),
            event_type=event_type,
            timestamp=datetime.now()
        )
        
        logger.info(f"Parsed PR event: {event_type} for PR #{pr_event.pr_id}")
        return pr_event
    
    def _map_event_type(self, event_key: str) -> str:
        """Map Bitbucket event key to our event type.
        
        Args:
            event_key: Bitbucket event key
            
        Returns:
            Event type string
        """
        mapping = {
            'pullrequest:created': 'created',
            'pullrequest:updated': 'updated',
            'pullrequest:approved': 'approved',
            'pullrequest:fulfilled': 'merged'
        }
        
        return mapping.get(event_key, 'updated')
    
    def should_review(self, pr_event: PREvent) -> bool:
        """Determine if PR should be reviewed.
        
        Args:
            pr_event: PREvent object
            
        Returns:
            True if should review
        """
        # Review on created and updated events
        return pr_event.event_type in ['created', 'updated']
