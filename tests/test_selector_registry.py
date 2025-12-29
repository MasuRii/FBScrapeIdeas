import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from scraper.selectors import SelectorRegistry, get_selector_registry


@pytest.fixture
def temp_selectors_file(tmp_path):
    """Fixture to provide a temporary path for learned selectors."""
    return str(tmp_path / "test_learned_selectors.json")


def test_selector_registry_init_defaults():
    """Test that SelectorRegistry initializes with default selectors."""
    registry = SelectorRegistry(learned_selectors_path="non_existent_file.json")

    # Check if defaults are loaded
    assert "article" in registry.selectors
    assert "content" in registry.selectors
    assert registry.selectors["article"] == SelectorRegistry.DEFAULT_SELECTORS["article"]
    assert registry.learned_selectors_path == "non_existent_file.json"


def test_get_selector_combined_string():
    """Test that get_selector returns a comma-separated string."""
    registry = SelectorRegistry(learned_selectors_path="none.json")
    registry.selectors = {"test_type": ["sel1", "sel2"]}

    result = registry.get_selector("test_type")
    assert result == "sel1, sel2"

    # Test unknown type
    assert registry.get_selector("unknown") == ""


def test_get_selectors_list():
    """Test that get_selectors_list returns the list of selectors."""
    registry = SelectorRegistry(learned_selectors_path="none.json")
    registry.selectors = {"test_type": ["sel1", "sel2"]}

    assert registry.get_selectors_list("test_type") == ["sel1", "sel2"]
    assert registry.get_selectors_list("unknown") == []


def test_add_alternative_learning(temp_selectors_file):
    """Test adding an alternative selector and persistence."""
    registry = SelectorRegistry(learned_selectors_path=temp_selectors_file)

    initial_count = len(registry.get_selectors_list("article"))
    new_selector = ".new-article-selector"

    registry.add_alternative("article", new_selector)

    # Verify it was added to memory
    assert new_selector in registry.selectors["article"]
    assert len(registry.selectors["article"]) == initial_count + 1

    # Verify it was persisted to disk
    assert os.path.exists(temp_selectors_file)
    with open(temp_selectors_file, "r") as f:
        data = json.load(f)
        assert "article" in data
        assert new_selector in data["article"]


def test_add_alternative_duplicate():
    """Test that duplicate selectors are not added."""
    registry = SelectorRegistry(learned_selectors_path="none.json")
    initial_selectors = list(registry.selectors["article"])

    registry.add_alternative("article", initial_selectors[0])
    assert registry.selectors["article"] == initial_selectors


def test_add_alternative_new_type(temp_selectors_file):
    """Test adding an alternative for a completely new element type."""
    registry = SelectorRegistry(learned_selectors_path=temp_selectors_file)
    registry.add_alternative("new_type", ".some-selector")

    assert ".some-selector" in registry.selectors["new_type"]


def test_load_learned_selectors(temp_selectors_file):
    """Test loading learned selectors from disk on initialization."""
    # Create a learned selectors file
    learned_data = {
        "article": [".learned-art"],
        "content": [".learned-cont"],
        "new_type": [".learned-new"],
    }
    with open(temp_selectors_file, "w") as f:
        json.dump(learned_data, f)

    registry = SelectorRegistry(learned_selectors_path=temp_selectors_file)

    assert ".learned-art" in registry.selectors["article"]
    assert ".learned-cont" in registry.selectors["content"]
    # Note: currently _load_learned_selectors only loads if the type is in self.selectors
    # Let's check the implementation:
    # if element_type in self.selectors:
    #     for sel in selectors:
    #         if sel not in self.selectors[element_type]:
    #             self.selectors[element_type].append(sel)

    # So 'new_type' should NOT be loaded if it's not in DEFAULT_SELECTORS
    assert "new_type" not in registry.selectors


def test_load_learned_selectors_corrupt(temp_selectors_file):
    """Test resilience against corrupt JSON."""
    with open(temp_selectors_file, "w") as f:
        f.write("corrupt json {")

    # Should not raise exception
    registry = SelectorRegistry(learned_selectors_path=temp_selectors_file)
    assert registry.selectors["article"] == SelectorRegistry.DEFAULT_SELECTORS["article"]


def test_save_learned_selectors_error():
    """Test handling of save errors (e.g., permission denied)."""
    # Use a path that has a directory component to avoid empty string in os.makedirs
    registry = SelectorRegistry(learned_selectors_path="test_dir/any.json")

    # Force an error during save by mocking open to raise PermissionError
    # We also mock os.makedirs to avoid it failing on the empty/invalid path
    with patch("os.makedirs", return_value=None):
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("scraper.selectors.logger") as mock_logger:
                # Must add a NEW selector to trigger save
                registry.add_alternative("article", ".wont-save")
                # Check that warning was called with the expected message
                args, _ = mock_logger.warning.call_args
                assert "Could not save learned selectors" in args[0]
                assert "Permission denied" in args[0]


def test_record_failure():
    """Test recording selector failures."""
    registry = SelectorRegistry(learned_selectors_path="none.json")

    with patch("scraper.selectors.logger") as mock_logger:
        registry.record_failure("article", ".failed-sel")
        assert ".failed-sel" in registry.failed_selectors["article"]
        mock_logger.warning.assert_called_with("Selector failed for 'article': .failed-sel")

    # Record same failure again
    registry.record_failure("article", ".failed-sel")
    assert registry.failed_selectors["article"].count(".failed-sel") == 1


def test_get_selector_registry_singleton():
    """Test that get_selector_registry returns a singleton instance."""
    reg1 = get_selector_registry()
    reg2 = get_selector_registry()
    assert reg1 is reg2
    assert isinstance(reg1, SelectorRegistry)


def test_default_path_generation():
    """Test that _get_default_path generates a path within the state directory."""
    with patch("scraper.selectors.SESSION_STATE_PATH", "some/path/session.json"):
        registry = SelectorRegistry()
        path = registry._get_default_path()
        assert "learned_selectors.json" in path
        # Normalize path for cross-platform comparison
        assert str(Path("some/path")) in str(Path(path))
