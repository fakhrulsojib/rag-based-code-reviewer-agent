"""Main FastAPI application."""
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.logger import logger
from src.models import ReviewRequest, ReviewResponse, Finding
from src.bitbucket.webhook_handler import WebhookHandler
from src.bitbucket.manual_review_handler import ManualReviewHandler
from src.workflow.review_graph import ReviewWorkflow
from src.workflow.reporter import ReviewReporter
import os
import json
from typing import List, Dict, Any


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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize handlers
webhook_handler = WebhookHandler()
manual_review_handler = ManualReviewHandler()
review_workflow = ReviewWorkflow()
reporter = ReviewReporter()


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


    # Create report directory upfront so we can return it
    report_path = reporter.create_report_dir(pr_id)
    report_dir_name = os.path.basename(report_path)
    
    # Initialize status file
    reporter.save_status(report_path, {
        "status": "pending",
        "pr_id": pr_id,
        "submitted_at": time.time()
    })
    
    # Run review in background
    background_tasks = BackgroundTasks()
    background_tasks.add_task(run_review, pr_id, report_dir_name)
    
    # We need to manually execute the background task because we are returning a response differently
    # actually FastAPI handles BackgroundTasks if passed as argument to endpoint logic or returned in response
    # But here I need to inject it into the response or run it manually. 
    # Better approach: Add BackgroundTasks to endpoint signature
    
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Review request accepted",
            "pr_id": pr_id,
            "report_dir": report_dir_name
        },
        background=background_tasks
    )

@app.post("/review/{pr_id}")
async def manual_review(pr_id: int, background_tasks: BackgroundTasks, request: ReviewRequest = None):
    """Manually trigger a PR review.
    
    Args:
        pr_id: Pull request ID
        background_tasks: FastAPI background tasks
        request: Optional review request parameters
        
    Returns:
        Review response (Accepted)
    """
    logger.info(f"Received manual review request for PR #{pr_id}")
    
    # Create request if not provided
    if request is None:
        request = ReviewRequest(pr_id=pr_id)
    
    # Validate request
    if not manual_review_handler.validate_request(request):
        raise HTTPException(status_code=400, detail="Invalid review request")
    
    # Create report directory upfront
    report_path = reporter.create_report_dir(pr_id)
    report_dir_name = os.path.basename(report_path)
    
    logger.info(f"Created report directory: {report_dir_name}")
    
    # Run review in background
    background_tasks.add_task(run_review, pr_id, report_dir_name)
    
    return {
        "status": "accepted",
        "message": "Review started in background",
        "pr_id": pr_id,
        "report_dir": report_dir_name
    }


@app.get("/reviews/{pr_id}")
@app.get("/reviews/{pr_id}/{report_id}")
async def get_review_results(pr_id: int, report_id: str = None):
    """Get review results for a PR.
    
    Args:
        pr_id: Pull Request ID
        report_id: Optional specific report directory name
        
    Returns:
        Aggregated review data including possible comments
    """
    latest_report_dir = None
    
    if report_id:
        # Validate and use provided report_id
        target_path = os.path.join(reporter.base_dir, report_id)
        if os.path.exists(target_path) and os.path.isdir(target_path):
             latest_report_dir = target_path
        else:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    else:
        # Find latest report dir for this PR
        report_dirs = []
        if os.path.exists(reporter.base_dir):
            for d in os.listdir(reporter.base_dir):
                if d.endswith(f"_{pr_id}") and os.path.isdir(os.path.join(reporter.base_dir, d)):
                    report_dirs.append(d)
        
        if not report_dirs:
            raise HTTPException(status_code=404, detail=f"No review reports found for PR {pr_id}")
        
        # Sort by timestamp (part of dirname)
        report_dirs.sort(reverse=True)
        latest_report_dir = os.path.join(reporter.base_dir, report_dirs[0])
    
    logger.info(f"Serving review results from {latest_report_dir}")
    
    # Read status.json if exists
    status_info = {}
    status_path = os.path.join(latest_report_dir, "status.json")
    if os.path.exists(status_path):
        with open(status_path, 'r') as f:
            status_info = json.load(f)
            
    # Aggregate chunks
    chunks_data = []
    
    # Iterate over chunk subdirectories
    for item in sorted(os.listdir(latest_report_dir)):
        if item.startswith("chunk_") and os.path.isdir(os.path.join(latest_report_dir, item)):
            chunk_path = os.path.join(latest_report_dir, item)
            chunk_id = int(item.split("_")[1])
            
            chunk_info = {
                "id": chunk_id,
                "diffs": [],
                "possible_comments": [],
                "posted_comments": []
            }
            
            # Load diffs
            diffs_path = os.path.join(chunk_path, "diffs.json")
            if os.path.exists(diffs_path):
                with open(diffs_path, 'r') as f:
                    chunk_info["diffs"] = json.load(f)
            
            # Load possible comments
            possible_path = os.path.join(chunk_path, "possible_comments.json")
            if os.path.exists(possible_path):
                with open(possible_path, 'r') as f:
                    chunk_info["possible_comments"] = json.load(f)
                    
            # Load posted comments
            posted_path = os.path.join(chunk_path, "posted_comments.json")
            if os.path.exists(posted_path):
                with open(posted_path, 'r') as f:
                    chunk_info["posted_comments"] = json.load(f)
            
            chunks_data.append(chunk_info)
            
    return {
        "pr_id": pr_id,
        "report_id": os.path.basename(latest_report_dir),
        "status": status_info.get("status", "unknown"),
        "total_chunks": status_info.get("total_chunks", 0),
        "completed_chunks": status_info.get("completed_chunks", 0),
        "chunks": chunks_data
    }


@app.post("/reviews/{pr_id}/comments")
@app.post("/reviews/{pr_id}/{report_id}/comments")
async def post_comment(pr_id: int, finding: Finding, report_id: str = None):
    """Post a comment to Bitbucket and record it.
    
    Args:
        pr_id: Pull Request ID
        finding: The finding/comment to post
        report_id: Optional report ID to target
        
    Returns:
        Status and posted comment
    """
    from src.bitbucket.comment_poster import CommentPoster
    comment_poster = CommentPoster()
    
    try:
        # 1. Post to Bitbucket
        await comment_poster.post_findings(pr_id, [finding])
        
        # 2. Append to posted_comments.json
        target_report_dir = None
        
        if report_id:
             target_path = os.path.join(reporter.base_dir, report_id)
             if os.path.exists(target_path):
                 target_report_dir = target_path
        
        if not target_report_dir:
            # Fallback to latest
            report_dirs = []
            if os.path.exists(reporter.base_dir):
                for d in os.listdir(reporter.base_dir):
                    if d.endswith(f"_{pr_id}") and os.path.isdir(os.path.join(reporter.base_dir, d)):
                        report_dirs.append(d)
            
            if report_dirs:
                report_dirs.sort(reverse=True)
                target_report_dir = os.path.join(reporter.base_dir, report_dirs[0])
        
        if target_report_dir:
            # Try to find the chunk this file belongs to
            target_chunk_dir = None
            
            for item in sorted(os.listdir(target_report_dir)):
                if item.startswith("chunk_") and os.path.isdir(os.path.join(target_report_dir, item)):
                    chunk_path = os.path.join(target_report_dir, item)
                    diffs_path = os.path.join(chunk_path, "diffs.json")
                    if os.path.exists(diffs_path):
                        with open(diffs_path, 'r') as f:
                            diffs = json.load(f)
                            for diff in diffs:
                                if diff.get('file_path') == finding.file:
                                    target_chunk_dir = chunk_path
                                    break
                if target_chunk_dir:
                    break
            
            if not target_chunk_dir:
                 # Fallback to chunk_0
                 target_chunk_dir = os.path.join(target_report_dir, "chunk_0")
                 if not os.path.exists(target_chunk_dir):
                     os.makedirs(target_chunk_dir)

            # Append to posted_comments.json
            posted_path = os.path.join(target_chunk_dir, "posted_comments.json")
            existing_comments = []
            if os.path.exists(posted_path):
                with open(posted_path, 'r') as f:
                    existing_comments = json.load(f)
            
            existing_comments.append(finding.dict())
            
            with open(posted_path, 'w') as f:
                json.dump(existing_comments, f, indent=2, default=str)
                
            logger.info(f"Recorded posted comment in {posted_path}")

        return {"status": "success", "message": "Comment posted"}
        
    except Exception as e:
        logger.error(f"Failed to post comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_review(pr_id: int, report_dir: str = None):
    """Run review workflow in background.
    
    Args:
        pr_id: Pull request ID
        report_dir: Optional report directory
    """
    try:
        logger.info(f"Running background review for PR #{pr_id}")
        await review_workflow.run(pr_id, report_dir)
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
