"""Anchor detection system for identifying code patterns."""
import re
import json
from typing import List, Dict, Set
from pathlib import Path
from src.models import Anchor, FileDiff
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
        r'\bCREATE\s+TABLE\b': ['ddl', 'schema', 'table-creation'],
        r'\bALTER\s+TABLE\b': ['ddl', 'schema', 'migration'],
        r'\bDROP\s+TABLE\b': ['ddl', 'schema'],
        r'\bCREATE\s+INDEX\b': ['ddl', 'index', 'performance'],
        r'\bINSERT\s+INTO\b': ['dml', 'data-manipulation'],
        r'\bUPDATE\b': ['dml', 'data-manipulation'],
        r'\bDELETE\s+FROM\b': ['dml', 'data-manipulation'],
        r'\bSELECT\b': ['query', 'data-retrieval'],
    }
    
    # General code patterns
    CODE_PATTERNS = {
        r'class\s+\w+\s+extends\s+': ['inheritance', 'oop'],
        r'class\s+\w+\s+implements\s+': ['interface', 'oop'],
        r'interface\s+\w+': ['interface', 'contract'],
        r'enum\s+\w+': ['enum', 'constants'],
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
        
        logger.info(f"Detected {len(anchors)} anchors for {file_diff.file_path}: {[a.tag for a in anchors]}")
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
