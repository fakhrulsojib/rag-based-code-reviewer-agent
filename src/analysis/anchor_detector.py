"""Anchor detection system for identifying code patterns."""
import re
import json
import asyncio
from typing import List, Dict, Set, Optional
from pathlib import Path
from src.models import Anchor, FileDiff
from src.ingestion.embedder import Embedder
from src.ingestion.vector_store import VectorStore
from src.logger import logger


class AnchorDetector:
    """Detects anchors (code patterns) in file diffs to determine relevant rules."""
    
    # File extension to anchor tag mapping
    EXTENSION_MAP = {
        '.java': ['java', 'backend'],
        '.sql': ['sql', 'database', 'migration'],
        '.js': ['javascript', 'frontend'],
        '.ts': ['typescript', 'frontend'],
        '.jsx': ['react', 'javascript', 'frontend'],
        '.tsx': ['react', 'typescript', 'frontend'],
        '.py': ['python', 'backend'],
        '.go': ['golang', 'backend'],
        '.xml': ['xml', 'config'],
        '.yml': ['yaml', 'config'],
        '.yaml': ['yaml', 'config'],
        '.json': ['json', 'config'],
        '.properties': ['properties', 'config'],
    }
    
    # Java annotation patterns
    JAVA_ANNOTATIONS = {
        '@Entity': ['jpa', 'entity', 'database', 'orm'],
        '@Table': ['jpa', 'entity', 'database'],
        '@RestController': ['web-layer', 'api', 'controller', 'rest'],
        '@Controller': ['web-layer', 'controller', 'mvc'],
        '@Service': ['service-layer', 'business-logic'],
        '@Repository': ['repository', 'data-access', 'database'],
        '@Component': ['spring', 'component'],
        '@Configuration': ['spring', 'config'],
        '@RequestMapping': ['web-layer', 'api', 'routing'],
        '@GetMapping': ['web-layer', 'api', 'rest'],
        '@PostMapping': ['web-layer', 'api', 'rest'],
        '@PutMapping': ['web-layer', 'api', 'rest'],
        '@DeleteMapping': ['web-layer', 'api', 'rest'],
    }
    
    # SQL keyword patterns
    SQL_PATTERNS = {
        r'\\bCREATE\\s+TABLE\\b': ['ddl', 'schema', 'table-creation'],
        r'\\bALTER\\s+TABLE\\b': ['ddl', 'schema', 'migration'],
        r'\\bDROP\\s+TABLE\\b': ['ddl', 'schema'],
        r'\\bCREATE\\s+INDEX\\b': ['ddl', 'index', 'performance'],
        r'\\bINSERT\\s+INTO\\b': ['dml', 'data-manipulation'],
        r'\\bUPDATE\\b': ['dml', 'data-manipulation'],
        r'\\bDELETE\\s+FROM\\b': ['dml', 'data-manipulation'],
        r'\\bSELECT\\b': ['query', 'data-retrieval'],
    }
    
    # General code patterns
    CODE_PATTERNS = {
        r'class\\s+\\w+\\s+extends\\s+': ['inheritance', 'oop'],
        r'class\\s+\\w+\\s+implements\\s+': ['interface', 'oop'],
        r'interface\\s+\\w+': ['interface', 'contract'],
        r'enum\\s+\\w+': ['enum', 'constants'],
        r'@Test': ['testing', 'unit-test'],
        r'@Override': ['override', 'inheritance'],
        r'serialVersionUID': ['serialization', 'entity'],
    }
    
    def __init__(self, custom_registry_path: str = None):
        """Initialize the anchor detector.
        
        Args:
            custom_registry_path: Path to custom anchor registry JSON file
        """
        self.custom_patterns = {}
        
        # Initialize RAG components for raw detection
        # Note: These are initialized lazily or shared if passed, but here we init them.
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        
        if custom_registry_path and Path(custom_registry_path).exists():
            self._load_custom_registry(custom_registry_path)
    
    def detect_anchors(self, file_diff: FileDiff) -> List[Anchor]:
        """Detect all anchors in a file diff.
        
        Args:
            file_diff: FileDiff object containing file path and diff content
            
        Returns:
            List of detected Anchor objects
        """
        anchors = []
        detected_tags = set()
        
        # 1. File extension detection
        ext_anchors = self._detect_by_extension(file_diff.file_path)
        for anchor in ext_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        # 2. Annotation detection (Java)
        if file_diff.file_path.endswith('.java'):
            ann_anchors = self._detect_java_annotations(file_diff.diff_content)
            for anchor in ann_anchors:
                if anchor.tag not in detected_tags:
                    anchors.append(anchor)
                    detected_tags.add(anchor.tag)
        
        # 3. SQL pattern detection
        if file_diff.file_path.endswith('.sql'):
            sql_anchors = self._detect_sql_patterns(file_diff.diff_content)
            for anchor in sql_anchors:
                if anchor.tag not in detected_tags:
                    anchors.append(anchor)
                    detected_tags.add(anchor.tag)
        
        # 4. General code pattern detection
        code_anchors = self._detect_code_patterns(file_diff.diff_content)
        for anchor in code_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        # 5. Custom pattern detection
        custom_anchors = self._detect_custom_patterns(file_diff.diff_content)
        for anchor in custom_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        # 6. Raw similarity detection (Asynchronous logic wrapped)
        # Since this method is synchronous but embedder/vector store might be async or used in async context...
        # Embedder.embed_query is async. VectorStore.query is sync.
        # We need to run async code here. But detect_anchors is called from async _detect_anchors in ReviewWorkflow.
        # We should make detect_anchors async or run it synchronously.
        # Embedder.embed_query IS async definition: `async def embed_query(...)`.
        # So we MUST make detect_anchors async or use run_until_complete.
        # However, making it async breaks the interface if called synchronously elsewhere.
        # But looking at ReviewWorkflow, it uses `self.anchor_detector.detect_anchors(file_diff)`.
        # ReviewWorkflow's `_detect_anchors` is async. So we can update `detect_anchors` to be async.
        # PROPOSAL: Make detect_anchors async.
        
        # Wait, I cannot easily change the signature in this tool call if it requires changing usage elsewhere efficiently.
        # ReviewWorkflow `_detect_anchors` calls it synchronously: `anchors = self.anchor_detector.detect_anchors(file_diff)`
        # I need to change ReviewWorkflow usage too if I make this async.
        # Alternatively, since I can't await here, I can use asyncio.run or loop.run_until_complete?
        # Check current loop.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are already in a loop (ReviewWorkflow.run). cannot use run_until_complete.
                # We should have made detect_anchors async. 
                # For now, I'll assume I can change `detect_anchors` signature to async and update ReviewWorkflow in next step if needed.
                # Actually, I already refactored ReviewWorkflow step 36. 
                # Line 120: `anchors = self.anchor_detector.detect_anchors(file_diff)`
                # I should update ReviewWorkflow to `await self.anchor_detector.detect_anchors(file_diff)`.
                
                # To be safe regarding 'single contiguous block', I will make `detect_anchors` async here.
                # AND I will have to update ReviewWorkflow to await it.
                pass
        except:
            pass
            
        # For now, let's implement validation: Raw Detector requires async execution.
        # I will change the signature to `async def detect_anchors`.
        
        # To handle existing synchronous callers (if any), I might need a wrapper.
        # But only ReviewWorkflow calls it.
        
        # Re-check the method body. I will assume I can await `_detect_by_similarity`.
        
        # We need to invoke `await self._detect_by_similarity(...)`
        # But wait, this method body is huge replacing everything.
        # I will define `async def detect_anchors`.
        pass
        
        # Since I'm restricted to `replace_file_content` which executes once...
        # I should provide the full new content with async.
        
        # Warning: `detect_anchors` was sync.
        # I will make it `async def detect_anchors`.
        
        # Wait, I must Ensure `_detect_by_similarity` logic is inside `detect_anchors`.
        
        # Let's write the code assuming async.
        
        raw_anchors = asyncio.run(self._detect_by_similarity(file_diff.diff_content)) \
            if not asyncio.get_event_loop().is_running() \
            else None # Problem.
            
        # Strategy: To function within the existing async event loop of ReviewWorkflow, `detect_anchors` MUST be async.
        # I will redefine `detect_anchors` as `async def`.
        # Then I will have to update `ReviewWorkflow` (which I just replaced!) to await it.
        
        return anchors 

    async def detect_anchors(self, file_diff: FileDiff) -> List[Anchor]:
        """Detect all anchors in a file diff.
        
        Args:
            file_diff: FileDiff object containing file path and diff content
            
        Returns:
            List of detected Anchor objects
        """
        anchors = []
        detected_tags = set()
        
        # 1. File extension detection
        ext_anchors = self._detect_by_extension(file_diff.file_path)
        for anchor in ext_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        # 2. Annotation detection (Java)
        if file_diff.file_path.endswith('.java'):
            ann_anchors = self._detect_java_annotations(file_diff.diff_content)
            for anchor in ann_anchors:
                if anchor.tag not in detected_tags:
                    anchors.append(anchor)
                    detected_tags.add(anchor.tag)
        
        # 3. SQL pattern detection
        if file_diff.file_path.endswith('.sql'):
            sql_anchors = self._detect_sql_patterns(file_diff.diff_content)
            for anchor in sql_anchors:
                if anchor.tag not in detected_tags:
                    anchors.append(anchor)
                    detected_tags.add(anchor.tag)
        
        # 4. General code pattern detection
        code_anchors = self._detect_code_patterns(file_diff.diff_content)
        for anchor in code_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        # 5. Custom pattern detection
        custom_anchors = self._detect_custom_patterns(file_diff.diff_content)
        for anchor in custom_anchors:
            if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)

        # 6. Raw similarity detection
        sim_anchors = await self._detect_by_similarity(file_diff.diff_content)
        for anchor in sim_anchors:
             if anchor.tag not in detected_tags:
                anchors.append(anchor)
                detected_tags.add(anchor.tag)
        
        logger.info(f"Detected {len(anchors)} anchors for {file_diff.file_path}: {[a.tag for a in anchors]}")
        return anchors
    
    async def _detect_by_similarity(self, content: str) -> List[Anchor]:
        """Detect anchors using vector similarity search.
        
        Args:
            content: Raw file content
            
        Returns:
            List of Anchor objects
        """
        anchors = []
        try:
            # Truncate content to avoid token limits (arbitrary reasonable limit)
            truncated_content = content[:2000]
            
            # Embed query
            embedding = await self.embedder.embed_query(truncated_content)
            
            # Query vector store
            # Use a generic query to find any relevant rule
            results = self.vector_store.query(
                query_embedding=embedding,
                top_k=3 # Top 3 most relevant rules
            )
            
            for rule_chunk in results:
                # Extract potential anchors from metadata
                meta = rule_chunk.chunk.metadata
                
                # Check for explicit tags
                if 'tags' in meta:
                    tags = meta['tags']
                    if isinstance(tags, str):
                        tags = [t.strip() for t in tags.split(',')]
                    elif isinstance(tags, list):
                        pass
                    else:
                        tags = []
                    
                    for tag in tags:
                        anchors.append(Anchor(tag=str(tag).lower(), confidence=0.6, source="similarity"))

                # Check for category
                if 'category' in meta:
                    cat = meta['category']
                    anchors.append(Anchor(tag=str(cat).lower(), confidence=0.6, source="similarity"))

        except Exception as e:
            logger.error(f"Error in raw similarity detection: {e}")
            
        return anchors

    def _detect_by_extension(self, file_path: str) -> List[Anchor]:
        """Detect anchors based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of Anchor objects
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in self.EXTENSION_MAP:
            tags = self.EXTENSION_MAP[ext]
            return [
                Anchor(tag=tag, confidence=1.0, source="extension")
                for tag in tags
            ]
        
        return []
    
    def _detect_java_annotations(self, content: str) -> List[Anchor]:
        """Detect Java annotations in content.
        
        Args:
            content: File content
            
        Returns:
            List of Anchor objects
        """
        anchors = []
        
        for annotation, tags in self.JAVA_ANNOTATIONS.items():
            if annotation in content:
                for tag in tags:
                    anchors.append(
                        Anchor(tag=tag, confidence=1.0, source="annotation")
                    )
        
        return anchors
    
    def _detect_sql_patterns(self, content: str) -> List[Anchor]:
        """Detect SQL patterns in content.
        
        Args:
            content: File content
            
        Returns:
            List of Anchor objects
        """
        anchors = []
        
        for pattern, tags in self.SQL_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                for tag in tags:
                    anchors.append(
                        Anchor(tag=tag, confidence=0.9, source="pattern")
                    )
        
        return anchors
    
    def _detect_code_patterns(self, content: str) -> List[Anchor]:
        """Detect general code patterns in content.
        
        Args:
            content: File content
            
        Returns:
            List of Anchor objects
        """
        anchors = []
        
        for pattern, tags in self.CODE_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                for tag in tags:
                    anchors.append(
                        Anchor(tag=tag, confidence=0.8, source="pattern")
                    )
        
        return anchors
    
    def _detect_custom_patterns(self, content: str) -> List[Anchor]:
        """Detect custom patterns from registry.
        
        Args:
            content: File content
            
        Returns:
            List of Anchor objects
        """
        anchors = []
        
        for pattern, tags in self.custom_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                for tag in tags:
                    anchors.append(
                        Anchor(tag=tag, confidence=0.7, source="pattern")
                    )
        
        return anchors
    
    def _load_custom_registry(self, registry_path: str):
        """Load custom anchor patterns from JSON file.
        
        Args:
            registry_path: Path to JSON file
        """
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            
            for item in registry:
                pattern = item.get('pattern')
                tags = item.get('tags', [])
                if pattern and tags:
                    self.custom_patterns[pattern] = tags
            
            logger.info(f"Loaded {len(self.custom_patterns)} custom patterns")
        except Exception as e:
            logger.error(f"Error loading custom registry: {e}")
    
    def get_anchor_tags(self, anchors: List[Anchor]) -> List[str]:
        """Extract unique tags from anchors.
        
        Args:
            anchors: List of Anchor objects
            
        Returns:
            List of unique tags
        """
        return list(set(anchor.tag for anchor in anchors))
