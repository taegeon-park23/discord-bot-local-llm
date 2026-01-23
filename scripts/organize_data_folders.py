import os
import shutil
import sys
import glob

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.tag_manager import TagManager
from src.logger import get_logger

# Configure logger to print to stdout for this script
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_frontmatter(filepath):
    """
    Rudimentary frontmatter parser.
    Returns a dict with 'category', 'title', etc.
    """
    meta = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines and lines[0].strip() == '---':
                for line in lines[1:]:
                    if line.strip() == '---': break
                    if ':' in line:
                        key, val = line.split(':', 1)
                        meta[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
    return meta

def organize_files():
    tag_manager = TagManager()
    
    # Identify existing subfolders that map to topics
    # We might have folders like "AI_LLM" that need to be remapped to "AI & ML"
    
    # 1. Scan all md files
    all_files = glob.glob(os.path.join(DATA_DIR, "**/*.md"), recursive=True)
    logger.info(f"Found {len(all_files)} markdown files.")

    moved_count = 0

    for filepath in all_files:
        filename = os.path.basename(filepath)
        current_dir_name = os.path.basename(os.path.dirname(filepath))
        
        # Decide topic
        topic = "Uncategorized"
        
        # Strategy 1: Check Frontmatter
        meta = load_frontmatter(filepath)
        categories = []
        if meta.get('category'):
            categories.append(meta['category'])
        
        # Strategy 2: Check Filename keywords (if frontmatter fails)
        # Split filename into words
        fname_keywords = filename.replace('_', ' ').replace('-', ' ').split()
        categories.extend(fname_keywords)

        # Strategy 3: Check current folder name if it's not 'data'
        if current_dir_name != 'data':
            categories.append(current_dir_name)
            
        # Get standardized topic
        topic = tag_manager.get_primary_topic(categories)
        
        # Target directory
        target_dir = os.path.join(DATA_DIR, topic)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        target_path = os.path.join(target_dir, filename)
        
        # Skip if already in the right place
        if os.path.abspath(target_path) == os.path.abspath(filepath):
            continue
            
        # Move file
        try:
            shutil.move(filepath, target_path)
            logger.info(f"Moved: {filename} -> {topic}/")
            moved_count += 1
        except Exception as e:
            logger.error(f"Failed to move {filename}: {e}")

    logger.info(f"Migration completed. Moved {moved_count} files.")
    
    # Cleanup empty directories
    for root, dirs, files in os.walk(DATA_DIR, topdown=False):
        for name in dirs:
            d = os.path.join(root, name)
            try:
                if not os.listdir(d):
                    os.rmdir(d)
                    logger.info(f"Removed empty directory: {d}")
            except: pass

if __name__ == "__main__":
    organize_files()
