"""LangGraph workflow for code review orchestration."""
import asyncio
import os
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from src.models import FileDiff, Anchor, RuleChunk, Finding
from src.bitbucket.diff_fetcher import DiffFetcher
from src.bitbucket.file_fetcher import FileFetcher
from src.analysis.anchor_detector import AnchorDetector
from src.retrieval.retriever import Retriever
from src.review.prompt_builder import PromptBuilder
from src.review.llm_client import LLMClient
from src.review.response_parser import ResponseParser
from src.bitbucket.comment_poster import CommentPoster
from src.workflow.partitioner import DiffPartitioner
from src.workflow.reporter import ReviewReporter
from src.config import settings
from src.logger import logger


class ReviewState(TypedDict):
    """State for the review workflow."""
    pr_id: int
    source_commit: str
    file_diffs: List[FileDiff]
    anchors: List[Anchor]
    anchor_tags: List[str]
    rule_chunks: List[RuleChunk]
    prompt: str
    llm_response: str
    findings: List[Finding]
    status: str
    error: str
    report_dir: str


class ReviewWorkflow:
    """LangGraph workflow for automated code review."""
    
    def __init__(self):
        """Initialize the review workflow."""
        self.diff_fetcher = DiffFetcher()
        self.file_fetcher = FileFetcher()
        self.anchor_detector = AnchorDetector()
        self.retriever = Retriever()
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()
        self.response_parser = ResponseParser()
        self.comment_poster = CommentPoster()
        self.partitioner = DiffPartitioner()
        self.reporter = ReviewReporter()
        
        # Build the workflow graph
        self.graph = self._build_graph()
        logger.info("Initialized review workflow")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(ReviewState)
        
        # Add nodes
        workflow.add_node("detect_anchors", self._detect_anchors)
        workflow.add_node("retrieve_rules", self._retrieve_rules)
        workflow.add_node("build_prompt", self._build_prompt)
        workflow.add_node("generate_review", self._generate_review)
        workflow.add_node("parse_response", self._parse_response)
        workflow.add_node("verify_findings", self._verify_findings)
        workflow.add_node("post_comments", self._post_comments)
        
        # Define edges
        workflow.set_entry_point("detect_anchors")
        workflow.add_edge("detect_anchors", "retrieve_rules")
        workflow.add_edge("retrieve_rules", "build_prompt")
        workflow.add_edge("build_prompt", "generate_review")
        workflow.add_edge("generate_review", "parse_response")
        workflow.add_edge("parse_response", "verify_findings")
        workflow.add_edge("verify_findings", "post_comments")
        workflow.add_edge("post_comments", END)
        
        return workflow.compile()
    
    async def _detect_anchors(self, state: ReviewState) -> ReviewState:
        """Detect anchors in file diffs.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Detecting anchors")
        
        try:
            all_anchors = []
            
            for file_diff in state['file_diffs']:
                anchors = await self.anchor_detector.detect_anchors(file_diff)
                all_anchors.extend(anchors)
            
            # Get unique anchor tags
            anchor_tags = self.anchor_detector.get_anchor_tags(all_anchors)
            
            state['anchors'] = all_anchors
            state['anchor_tags'] = anchor_tags
            state['status'] = 'anchors_detected'
        except Exception as e:
            logger.error(f"Error detecting anchors: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def _retrieve_rules(self, state: ReviewState) -> ReviewState:
        """Retrieve relevant rules from vector store.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Retrieving rules")
        
        try:

            if settings.force_use_all_rules:
                logger.info("Force use all rules enabled, retrieving all rules")
                state['rule_chunks'] = self.retriever.retrieve_all_rules()
            elif not state['anchor_tags']:
                logger.warning("No anchors detected, skipping rule retrieval")
                state['rule_chunks'] = []
            else:
                rule_chunks = await self.retriever.retrieve_rules(state['anchor_tags'])
                state['rule_chunks'] = rule_chunks
            
            state['status'] = 'rules_retrieved'
        except Exception as e:
            logger.error(f"Error retrieving rules: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def _build_prompt(self, state: ReviewState) -> ReviewState:
        """Build review prompt.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Building prompt")
        
        try:
            prompt = self.prompt_builder.build_review_prompt(
                file_diffs=state['file_diffs'],
                rule_chunks=state['rule_chunks']
            )
            state['prompt'] = prompt
            state['status'] = 'prompt_built'
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def _generate_review(self, state: ReviewState) -> ReviewState:
        """Generate review using LLM.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Generating review")
        
        try:
            response = await self.llm_client.generate_review(state['prompt'])
            state['llm_response'] = response
            state['status'] = 'review_generated'
        except Exception as e:
            logger.error(f"Error generating review: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def _parse_response(self, state: ReviewState) -> ReviewState:
        """Parse LLM response into findings.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Parsing response")
        
        try:
            findings = self.response_parser.parse_findings(state['llm_response'])
            validated_findings = self.response_parser.validate_findings(findings)
            state['findings'] = validated_findings
            state['status'] = 'response_parsed'
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def _verify_findings(self, state: ReviewState) -> ReviewState:
        """Verify findings against actual file content.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Verifying findings")
        
        try:
            verified_findings = []
            
            # Group findings by file to minimize API calls
            findings_by_file = {}
            for finding in state['findings']:
                if finding.file not in findings_by_file:
                    findings_by_file[finding.file] = []
                findings_by_file[finding.file].append(finding)
            
            for file_path, findings in findings_by_file.items():
                # Fetch file content
                content = await self.file_fetcher.fetch_file_content(file_path, state['source_commit'])
                if not content:
                    logger.warning(f"Could not fetch content for {file_path}, skipping verification")
                    verified_findings.extend(findings)
                    continue
                
                lines = content.split('\n')
                
                for finding in findings:
                    if not finding.code_snippet:
                        # No snippet to verify, keep original line
                        verified_findings.append(finding)
                        continue
                    
                    # Search for snippet in file
                    found_line = -1
                    snippet = finding.code_snippet.strip()
                    
                    # First check if the original line matches
                    if finding.line and 0 <= finding.line - 1 < len(lines):
                        if snippet in lines[finding.line - 1]:
                            found_line = finding.line
                    
                    # If not found at expected line, search the whole file
                    if found_line == -1:
                        for i, line in enumerate(lines):
                            if snippet in line:
                                found_line = i + 1
                                logger.info(f"Corrected line for {file_path}: {finding.line} -> {found_line}")
                                break
                    
                    if found_line != -1:
                        finding.line = found_line
                        verified_findings.append(finding)
                    else:
                        logger.warning(f"Could not verify snippet '{snippet}' in {file_path}")
                        # Keep finding but maybe mark as unverified? For now just keep it.
                        verified_findings.append(finding)
            
            state['findings'] = verified_findings
            state['status'] = 'findings_verified'
            
        except Exception as e:
            logger.error(f"Error verifying findings: {e}")
            # Don't fail the whole workflow, just proceed with unverified findings
            state['status'] = 'verification_failed'
        
        return state

    async def _post_comments(self, state: ReviewState) -> ReviewState:
        """Post review comments to Bitbucket.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        logger.info("Posting comments")
        
        try:
            # if state['findings']:
            #     # await self.comment_poster.post_findings(
            #     #     pr_id=state['pr_id'],
            #     #     findings=state['findings']
            #     # )
            
            state['status'] = 'complete'
        except Exception as e:
            logger.error(f"Error posting comments: {e}")
            state['error'] = str(e)
            state['status'] = 'error'
        
        return state
    
    async def run(self, pr_id: int, report_dir: str = None) -> ReviewState:
        """Run the complete review workflow with partitioning.
        
        Args:
            pr_id: Pull request ID
            report_dir: Optional pre-created report directory
            
        Returns:
            Final workflow state (aggregated)
        """
        logger.info(f"Starting review workflow for PR #{pr_id}")
        
        final_state: ReviewState = {
            'pr_id': pr_id,
            'source_commit': '',
            'file_diffs': [],
            'anchors': [],
            'anchor_tags': [],
            'rule_chunks': [],
            'prompt': '',
            'llm_response': '',
            'findings': [],
            'status': 'started',
            'error': '',
            'report_dir': ''
        }
        
        try:
            # 1. Fetch Diff
            file_diffs = await self.diff_fetcher.fetch_pr_diff(pr_id)
            pr_metadata = await self.diff_fetcher.get_pr_metadata(pr_id)
            final_state['source_commit'] = pr_metadata['source']['commit']['hash']
            final_state['file_diffs'] = file_diffs
            
            # 2. Partition Diff
            chunks = self.partitioner.partition_diffs(file_diffs)
            
            # 3. Create Report Directory (if not provided)
            if not report_dir:
                report_dir_path = self.reporter.create_report_dir(pr_id)
                report_dir = os.path.basename(report_dir_path)
            else:
                report_dir_path = os.path.join(self.reporter.base_dir, report_dir)
                
            final_state['report_dir'] = report_dir
            
            # Save initial status
            self.reporter.save_status(report_dir_path, {
                "status": "in_progress",
                "pr_id": pr_id,
                "total_chunks": len(chunks),
                "completed_chunks": 0,
                "current_chunk": 0,
                "start_time": time.time()
            })
            
            all_findings = []
            
            # 4. Process Chunks
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                # Report: Save diffs
                self.reporter.save_chunk_data(report_dir, i, chunk)
                
                # Initialize chunk state
                chunk_state: ReviewState = {
                    'pr_id': pr_id,
                    'source_commit': final_state['source_commit'],
                    'file_diffs': chunk,
                    'anchors': [],
                    'anchor_tags': [],
                    'rule_chunks': [],
                    'prompt': '',
                    'llm_response': '',
                    'findings': [],
                    'status': 'started',
                    'error': ''
                }
                
                # Run graph for this chunk
                result_state = await self.graph.ainvoke(chunk_state)
                
                # Report: Save artifacts
                self.reporter.save_anchors(report_dir, i, result_state.get('anchors', []))
                self.reporter.save_rules(report_dir, i, result_state.get('rule_chunks', []))
                self.reporter.save_prompt(report_dir, i, result_state.get('prompt', ''))
                self.reporter.save_response(
                    report_dir, 
                    i, 
                    result_state.get('llm_response', ''),
                    result_state.get('findings', [])
                )
                self.reporter.save_possible_comments(report_dir, i, result_state.get('findings', []))
                
                if result_state.get('error'):
                    logger.error(f"Error processing chunk {i}: {result_state['error']}")
                    final_state['error'] += f"Chunk {i} error: {result_state['error']}; "
                
                if result_state.get('findings'):
                    all_findings.extend(result_state['findings'])

                # Update status
                self.reporter.save_status(report_dir_path, {
                    "status": "in_progress",
                    "pr_id": pr_id,
                    "total_chunks": len(chunks),
                    "completed_chunks": i + 1,
                    "current_chunk": i + 1,
                    "last_updated": time.time()
                })
            
            final_state['findings'] = all_findings
            final_state['status'] = 'complete' if not final_state['error'] else 'partial_error'
            
            # Save final status
            self.reporter.save_status(report_dir_path, {
                "status": final_state['status'],
                "pr_id": pr_id,
                "total_chunks": len(chunks),
                "completed_chunks": len(chunks),
                "end_time": time.time(),
                "error": final_state['error']
            })
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            final_state['error'] = str(e)
            final_state['status'] = 'error'
            
            # Save error status
            if 'report_dir_path' in locals():
                self.reporter.save_status(report_dir_path, {
                    "status": "error",
                    "pr_id": pr_id,
                    "error": str(e),
                    "end_time": time.time()
                })
        
        return final_state
