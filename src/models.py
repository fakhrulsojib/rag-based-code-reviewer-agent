"""Data models for the code review agent."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


class Chunk(BaseModel):
    """Represents a chunk of a rule document."""
    
    content: str = Field(description="The text content of the chunk")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the chunk"
    )
    chunk_id: str = Field(description="Unique identifier for the chunk")
    source_file: str = Field(description="Source rule file path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "All JPA entities must include serialVersionUID",
                "metadata": {
                    "category": "java-entity",
                    "severity": "High",
                    "applies_to": ["@Entity"]
                },
                "chunk_id": "java-entity-001",
                "source_file": "rules/java-entity-rules.md"
            }
        }


class Anchor(BaseModel):
    """Represents a detected code pattern or anchor."""
    
    tag: str = Field(description="The anchor tag (e.g., 'entity', 'sql')")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score"
    )
    source: Literal["extension", "annotation", "pattern", "keyword"] = Field(
        description="How the anchor was detected"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "tag": "entity",
                "confidence": 1.0,
                "source": "annotation"
            }
        }


class Finding(BaseModel):
    """Represents a code review finding."""
    
    file: str = Field(description="File path relative to repo root")
    line: Optional[int] = Field(default=None, description="Line number")
    severity: Literal["High", "Medium", "Low"] = Field(description="Severity level")
    rule: str = Field(description="Rule that was violated")
    suggestion: str = Field(description="Suggested fix or improvement")
    category: Optional[str] = Field(default=None, description="Rule category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file": "src/entities/User.java",
                "line": 15,
                "severity": "High",
                "rule": "Missing serialVersionUID",
                "suggestion": "Add: private static final long serialVersionUID = 1L;",
                "category": "java-entity"
            }
        }


class PREvent(BaseModel):
    """Represents a Bitbucket pull request event."""
    
    pr_id: int = Field(description="Pull request ID")
    title: str = Field(description="PR title")
    source_branch: str = Field(description="Source branch name")
    destination_branch: str = Field(description="Destination branch name")
    author: str = Field(description="PR author username")
    event_type: Literal["created", "updated", "approved", "merged"] = Field(
        description="Type of PR event"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "pr_id": 123,
                "title": "Add user authentication",
                "source_branch": "feature/auth",
                "destination_branch": "develop",
                "author": "john.doe",
                "event_type": "created",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class FileDiff(BaseModel):
    """Represents a file diff from a pull request."""
    
    file_path: str = Field(description="Path to the file")
    diff_content: str = Field(description="Unified diff content")
    change_type: Literal["added", "modified", "deleted"] = Field(
        description="Type of change"
    )
    additions: int = Field(default=0, ge=0, description="Number of lines added")
    deletions: int = Field(default=0, ge=0, description="Number of lines deleted")
    annotated_content: Optional[str] = Field(default=None, description="Diff content with explicit line numbers")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "src/User.java",
                "diff_content": "+import javax.persistence.Entity;\n+@Entity\npublic class User {",
                "change_type": "modified",
                "additions": 2,
                "deletions": 0
            }
        }


class ReviewRequest(BaseModel):
    """Request model for manual PR review."""
    
    pr_id: int = Field(description="Pull request ID to review")
    force_refresh: bool = Field(
        default=False,
        description="Force re-review even if already reviewed"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pr_id": 123,
                "force_refresh": False
            }
        }


class ReviewResponse(BaseModel):
    """Response model for review operations."""
    
    pr_id: int = Field(description="Pull request ID")
    status: Literal["success", "error", "partial"] = Field(description="Review status")
    findings_count: int = Field(default=0, ge=0, description="Number of findings")
    findings: List[Finding] = Field(default_factory=list, description="List of findings")
    message: str = Field(description="Status message")
    processing_time: float = Field(default=0.0, ge=0.0, description="Processing time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pr_id": 123,
                "status": "success",
                "findings_count": 3,
                "findings": [],
                "message": "Review completed successfully",
                "processing_time": 5.2
            }
        }


class RuleChunk(BaseModel):
    """Represents a retrieved rule chunk with relevance score."""
    
    chunk: Chunk = Field(description="The rule chunk")
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score from vector search"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk": {
                    "content": "All entities must have serialVersionUID",
                    "metadata": {"severity": "High"},
                    "chunk_id": "001",
                    "source_file": "rules/java.md"
                },
                "relevance_score": 0.92
            }
        }
