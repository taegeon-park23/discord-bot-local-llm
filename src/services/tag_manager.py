import os
import yaml
from typing import List, Set, Dict, Optional
from src.logger import get_logger

logger = get_logger(__name__)

class TagManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TagManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, mapping_file: str = "src/data/tag_mapping.yaml"):
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        self.mapping_file = mapping_file
        self.mappings: List[Dict] = []
        self._load_mapping()
        self.initialized = True

    def _load_mapping(self):
        """Loads tag mappings from the YAML file."""
        # Check absolute path or relative to project root
        if not os.path.exists(self.mapping_file):
            # Try finding it relative to current working directory if not absolute
            if os.path.exists(os.path.join(os.getcwd(), self.mapping_file)):
                 self.mapping_file = os.path.join(os.getcwd(), self.mapping_file)
            else:
                logger.warning(f"Tag mapping file not found at {self.mapping_file}. Tag normalization will be skipped.")
                return

        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'mappings' in data:
                    self.mappings = data['mappings']
                    logger.info(f"Loaded {len(self.mappings)} tag mapping rules.")
                else:
                    logger.warning("Tag mapping file is empty or invalid structure.")
        except Exception as e:
            logger.error(f"Failed to load tag mappings: {e}")

    def normalize_tags(self, raw_tags: List[str]) -> List[str]:
        """
        Converts a list of raw tags into standardized topics based on loaded mappings.
        Returns a list of unique standardized topics.
        """
        if not raw_tags:
            return []

        normalized_topics: Set[str] = set()
        
        # Pre-process mappings for faster lookup could be done in __init__, 
        # but looping is fine for small N.
        
        for raw_tag in raw_tags:
            if not isinstance(raw_tag, str): 
                continue
                
            clean_tag = raw_tag.replace(" ", "").lower()
            matched = False
            
            for group in self.mappings:
                topic = group.get('topic')
                synonyms = group.get('synonyms', [])
                
                # Check if the raw tag is in synonyms (case-insensitive)
                # We strip spaces from synonyms for matching purposes too? 
                # Let's keep it simple: exact lower match or partial match?
                # The plan said "Lower-case and strip whitespace for matching".
                
                # Check strict match against synonyms
                if any(s.replace(" ", "").lower() == clean_tag for s in synonyms):
                    normalized_topics.add(topic)
                    matched = True
                    break
            
            # If no match found, what to do?
            # Plan: "If no match is found, preserve the original tag"
            if not matched:
                normalized_topics.add(raw_tag)

        return sorted(list(normalized_topics))

    def reload(self):
        """Reloads the mapping configuration."""
        self._load_mapping()

    def get_primary_topic(self, raw_tags: list) -> str:
        """
        Returns the single most relevant topic for a list of tags.
        Prioritizes mapped topics over raw tags.
        Returns 'Uncategorized' if no mapped topic is found.
        """
        normalized = self.normalize_tags(raw_tags)
        
        # Filter for known topics from mappings
        known_topics = set()
        for group in self.mappings:
            known_topics.add(group['topic'])
            
        # Find intersections
        valid_matches = [t for t in normalized if t in known_topics]
        
        if valid_matches:
            # Return the first known topic
            return sorted(valid_matches)[0]
            
        # Fallback: strict 'Uncategorized' to avoid random folder creation like '(Visual'
        return "Uncategorized"
