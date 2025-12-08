"""Main FastAPI application."""
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from src.config import settings
from src.logger import logger
from src.models import ReviewRequest, ReviewResponse
from src.bitbucket.webhook_handler import WebhookHandler
from src.bitbucket.manual_review_handler import ManualReviewHandler
from src.workflow.review_graph import ReviewWorkflow


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Startup
    logger.info("Starting Code Review Agent")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Vector Store: {settings.vector_store_type}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Code Review Agent")


# Create FastAPI app
app = FastAPI(
    title="Code Review Agent",
    description="Automated code review agent with RAG-based rule retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize handlers
webhook_handler = WebhookHandler()
manual_review_handler = ManualReviewHandler()
review_workflow = ReviewWorkflow()


@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "vector_store": settings.vector_store_type
    }


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Bitbucket webhook events.
    
    Args:
        request: FastAPI request
        background_tasks: Background tasks manager
        
    Returns:
        Acknowledgment response
    """
    logger.info("Received webhook request")
    
    # Validate webhook signature
    await webhook_handler.validate_webhook(request)
    
    # Parse PR event
    pr_event = await webhook_handler.parse_pr_event(request)
    
    # Check if we should review this PR
    if not webhook_handler.should_review(pr_event):
        logger.info(f"Skipping review for event type: {pr_event.event_type}")
        return {"status": "skipped", "reason": f"Event type {pr_event.event_type} not configured for review"}
    
    # Trigger review in background
    background_tasks.add_task(run_review, pr_event.pr_id)
    
    return {
        "status": "accepted",
        "pr_id": pr_event.pr_id,
        "message": "Review started in background"
    }


@app.post("/review/{pr_id}", response_model=ReviewResponse)
async def manual_review(pr_id: int, request: ReviewRequest = None):
    """Manually trigger a PR review.
    
    Args:
        pr_id: Pull request ID
        request: Optional review request parameters
        
    Returns:
        Review response
    """
    logger.info(f"Received manual review request for PR #{pr_id}")
    
    # Create request if not provided
    if request is None:
        request = ReviewRequest(pr_id=pr_id)
    
    # Validate request
    if not manual_review_handler.validate_request(request):
        raise HTTPException(status_code=400, detail="Invalid review request")
    
    # Run review
    start_time = time.time()
    
    try:
        final_state = await review_workflow.run(pr_id)
        
        processing_time = time.time() - start_time
        
        # Build response
        if final_state['status'] == 'complete':
            response = ReviewResponse(
                pr_id=pr_id,
                status='success',
                findings_count=len(final_state['findings']),
                findings=final_state['findings'],
                message="Review completed successfully",
                processing_time=processing_time
            )
        elif final_state['status'] == 'error':
            response = ReviewResponse(
                pr_id=pr_id,
                status='error',
                findings_count=0,
                findings=[],
                message=f"Review failed: {final_state.get('error', 'Unknown error')}",
                processing_time=processing_time
            )
        else:
            response = ReviewResponse(
                pr_id=pr_id,
                status='partial',
                findings_count=len(final_state.get('findings', [])),
                findings=final_state.get('findings', []),
                message=f"Review partially completed with status: {final_state['status']}",
                processing_time=processing_time
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during manual review: {e}")
        processing_time = time.time() - start_time
        
        return ReviewResponse(
            pr_id=pr_id,
            status='error',
            findings_count=0,
            findings=[],
            message=f"Review failed: {str(e)}",
            processing_time=processing_time
        )


async def run_review(pr_id: int):
    """Run review workflow in background.
    
    Args:
        pr_id: Pull request ID
    """
    try:
        logger.info(f"Running background review for PR #{pr_id}")
        await review_workflow.run(pr_id)
        logger.info(f"Background review completed for PR #{pr_id}")
    except Exception as e:
        logger.error(f"Error in background review for PR #{pr_id}: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler.
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        Error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False
    )
