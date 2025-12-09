import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from src.bitbucket.diff_fetcher import DiffFetcher
from src.bitbucket.comment_poster import CommentPoster
from src.models import Finding
from src.logger import logger

async def run_check():
    fetcher = DiffFetcher()
    poster = CommentPoster()
    pr_id = 1233
    
    # 1. Fetch Diff
    print(f"Fetching diff for PR {pr_id}...")
    file_diffs = await fetcher.fetch_pr_diff(pr_id)
    
    target_file = "atch-app/src/main/java/net/therap/batch/exdf/AbstractExdfJobRunner.java"
    target_line = 45
    
    found_diff = None
    for fd in file_diffs:
        if fd.file_path == target_file:
            found_diff = fd
            break
            
    if not found_diff:
        print(f"File {target_file} not found in diffs. Available code paths:")
        for fd in file_diffs:
            print(f"  - {fd.file_path}")
        return

    print(f"Found file: {found_diff.file_path}")
    print("Checking annotated content for line mapping...")
    
    # Check if line 45 exists in annotated content
    lines = found_diff.annotated_content.split('\n')
    line_exists = False
    for line in lines:
        if line.startswith(f"{target_line}:"):
            print(f"Line {target_line} FOUND in diff: {line}")
            line_exists = True
            break
            
    if not line_exists:
        print(f"Line {target_line} NOT FOUND in annotated diff.")
        # Print a few lines around to see what's there
        print("First 20 lines of annotated content:")
        for line in lines[:20]:
            print(line)
            
    # 2. Try to post a test comment if the line exists (or even if it doesn't, to see what happens)
    # The user asked to fix it by testing on PR 1233.
    # checking if I can make a test comment.
    
    finding = Finding(
        file=target_file,
        line=target_line,
        code_snippet="Test Snippet",
        severity="Low",
        rule="Test Rule",
        suggestion="[TEST] Debugging comment placement agent wtf",
        category="debug"
    )
    
    # Uncomment to actually post
    # print("Posting test comment...")
    # await poster.post_findings(pr_id, [finding])

if __name__ == "__main__":
    asyncio.run(run_check())
