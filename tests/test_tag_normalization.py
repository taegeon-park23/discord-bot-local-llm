import sys
import os
import unittest

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.tag_manager import TagManager

class TestTagManager(unittest.TestCase):
    def setUp(self):
        # Ensure we are using the project's mapping file
        # The TagManager defaults to "src/data/tag_mapping.yaml" relative to CWD
        # When running from project root, this should work.
        self.tm = TagManager()

    def test_normalization_development(self):
        print("\n[Test] Development Tags (python3, Coding, git)")
        raw = ["python3", "Coding", "git"]
        result = self.tm.normalize_tags(raw)
        print(f" -> Result: {result}")
        self.assertIn("Development", result)
        self.assertEqual(len(result), 1) # Should deduplicate to just "Development" since all 3 map to it

    def test_normalization_ai(self):
        print("\n[Test] AI Tags (LLM, gpt, openai)")
        raw = ["LLM", "gpt", "openai"]
        result = self.tm.normalize_tags(raw)
        print(f" -> Result: {result}")
        self.assertIn("AI & ML", result)

    def test_normalization_cloud(self):
        print("\n[Test] Cloud Tags (docker, AWS)")
        raw = ["docker", "AWS"]
        result = self.tm.normalize_tags(raw)
        print(f" -> Result: {result}")
        self.assertIn("DevOps & Cloud", result)

    def test_uncategorized_preservation(self):
        print("\n[Test] Uncategorized Tag (Cooking)")
        raw = ["Cooking"]
        result = self.tm.normalize_tags(raw)
        print(f" -> Result: {result}")
        self.assertIn("Cooking", result)

    def test_mixed(self):
        print("\n[Test] Mixed Tags (python, Cooking)")
        raw = ["python", "Cooking"]
        result = self.tm.normalize_tags(raw)
        print(f" -> Result: {result}")
        self.assertIn("Development", result)
        self.assertIn("Cooking", result)

if __name__ == '__main__':
    unittest.main()
