"""Query builder for constructing semantic search queries from anchors."""
from typing import List
from src.logger import logger


class QueryBuilder:
    """Builds semantic search queries from anchor tags."""
    
    # Anchor tag to natural language mapping
    TAG_DESCRIPTIONS = {
        # Languages
        'java': 'Java programming',
        'python': 'Python programming',
        'javascript': 'JavaScript programming',
        'typescript': 'TypeScript programming',
        'sql': 'SQL database',
        
        # Java frameworks
        'jpa': 'JPA entity',
        'entity': 'database entity',
        'spring': 'Spring framework',
        'orm': 'object-relational mapping',
        
        # Architecture layers
        'web-layer': 'web layer controller',
        'service-layer': 'service layer business logic',
        'repository': 'repository data access',
        'controller': 'controller',
        'api': 'REST API',
        
        # Database
        'database': 'database',
        'migration': 'database migration',
        'ddl': 'DDL schema definition',
        'dml': 'DML data manipulation',
        'schema': 'database schema',
        
        # Patterns
        'rest': 'RESTful API',
        'mvc': 'MVC pattern',
        'oop': 'object-oriented programming',
        'interface': 'interface design',
        'inheritance': 'class inheritance',
        
        # Frontend
        'react': 'React components',
        'frontend': 'frontend development',
        
        # Other
        'config': 'configuration',
        'testing': 'unit testing',
        'serialization': 'object serialization',
    }
    
    def build_query(self, anchor_tags: List[str]) -> str:
        """Build a natural language query from anchor tags.
        
        Args:
            anchor_tags: List of anchor tags
            
        Returns:
            Natural language query string
        """
        if not anchor_tags:
            return "general code review guidelines"
        
        # Convert tags to descriptions
        descriptions = []
        for tag in anchor_tags:
            desc = self.TAG_DESCRIPTIONS.get(tag, tag.replace('-', ' '))
            descriptions.append(desc)
        
        # Build query
        if len(descriptions) == 1:
            query = f"{descriptions[0]} guidelines and best practices"
        elif len(descriptions) == 2:
            query = f"{descriptions[0]} and {descriptions[1]} guidelines"
        else:
            # Take top 3 most specific tags
            top_tags = descriptions[:3]
            query = f"{', '.join(top_tags[:-1])}, and {top_tags[-1]} guidelines"
        
        logger.info(f"Built query from tags {anchor_tags}: '{query}'")
        return query
    
    def build_metadata_filter(self, anchor_tags: List[str]) -> dict:
        """Build metadata filter for vector store query.
        
        Args:
            anchor_tags: List of anchor tags
            
        Returns:
            Metadata filter dictionary
        """
        # For now, we don't use strict metadata filtering
        # to allow for related rules to be retrieved
        # This can be customized based on specific needs
        return {}
