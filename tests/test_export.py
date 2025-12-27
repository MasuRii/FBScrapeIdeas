import os
import json
import csv
import pytest
from export import exporter
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_data():
    """Fixture to provide sample data for export tests."""
    return {
        "posts": [
            {
                "internal_post_id": 1,
                "post_url": "https://fb.com/p1",
                "post_author_name": "Author 1",
                "post_content_raw": "Content 1",
                "posted_at": "2023-01-01",
                "ai_category": "Idea",
            },
            {
                "internal_post_id": 2,
                "post_url": "https://fb.com/p2",
                "post_author_name": "Author 2",
                "post_content_raw": "Content 2",
                "posted_at": "2023-01-02",
                "ai_category": "Question",
            },
        ],
        "comments": [
            {
                "comment_id": 1,
                "internal_post_id": 1,
                "commenter_name": "Commenter 1",
                "comment_text": "Comment 1",
                "commented_at": "2023-01-01",
            }
        ],
        "groups": [
            {"group_id": 1, "group_name": "Test Group", "group_url": "https://fb.com/groups/test"}
        ],
        "combined": [],  # Will be populated if needed, but exporter handles it
    }


def test_get_output_paths():
    """Test generating export paths."""
    base_path = "output/data"
    paths = exporter.get_output_paths(base_path, "csv")

    assert "posts" in paths
    assert paths["posts"].endswith("data_posts.csv")
    assert "comments" in paths
    assert paths["comments"].endswith("data_comments.csv")

    # Test directory path
    output_dir = "output_test_dir"
    os.makedirs(output_dir, exist_ok=True)
    try:
        paths_dir = exporter.get_output_paths(output_dir, "json")
        assert paths_dir["posts"].endswith("fbdata_posts.json")
    finally:
        if os.path.exists(output_dir):
            os.rmdir(output_dir)


def test_normalize_records_posts(sample_data):
    """Test record normalization for posts."""
    normalized, fieldnames = exporter.normalize_records(sample_data["posts"], "posts")

    assert len(normalized) == 2
    assert "post_url" in fieldnames
    assert "post_author_name" in fieldnames
    assert normalized[0]["post_url"] == "https://fb.com/p1"


def test_normalize_records_combined(sample_data):
    """Test record normalization for combined data."""
    combined_raw = sample_data["posts"] + sample_data["comments"] + sample_data["groups"]
    normalized, fieldnames = exporter.normalize_records(combined_raw, "combined")

    assert len(normalized) == 4
    # Check types
    types = [r["record_type"] for r in normalized]
    assert "post" in types
    assert "comment" in types
    assert "group" in types


def test_export_to_csv(tmp_path, sample_data):
    """Test exporting data to CSV files."""
    output_dir = tmp_path / "export"
    output_base = output_dir / "test_data"

    # Exporter expects a string path
    exporter.export_to_csv(sample_data, str(output_base))

    # Verify files created
    assert os.path.exists(output_dir / "test_data_posts.csv")
    assert os.path.exists(output_dir / "test_data_comments.csv")
    assert os.path.exists(output_dir / "test_data_groups.csv")

    # Verify content of posts CSV
    with open(output_dir / "test_data_posts.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["post_author_name"] == "Author 1"


def test_export_to_json(tmp_path, sample_data):
    """Test exporting data to JSON files."""
    output_dir = tmp_path / "json_export"
    output_base = output_dir / "test_data"

    exporter.export_to_json(sample_data, str(output_base))

    # Verify files created
    assert os.path.exists(output_dir / "test_data_posts.json")

    # Verify content
    with open(output_dir / "test_data_posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 2
        assert data[1]["post_author_name"] == "Author 2"


@patch("database.crud.list_groups")
@patch("database.crud.get_all_categorized_posts")
@patch("database.crud.get_comments_for_post")
def test_fetch_data_for_export(mock_comments, mock_posts, mock_groups, sample_data):
    """Test fetching data for export using mocked CRUD functions."""
    mock_groups.return_value = sample_data["groups"]
    mock_posts.return_value = sample_data["posts"]
    mock_comments.return_value = sample_data["comments"]

    conn = MagicMock()
    filters = {"category": "Idea"}

    result = exporter.fetch_data_for_export(conn, filters, entity="all")

    assert len(result["groups"]) == 1
    assert len(result["posts"]) == 2
    # mock_comments is called for each post. Since mock_posts returns 2 posts, it's called twice.
    assert len(result["comments"]) == 2  # 1 comment per post call (mocked)
    assert len(result["combined"]) == 5  # 1 group + 2 posts + 2 comments

    mock_groups.assert_called_once()
    mock_posts.assert_called()


def test_ensure_base_dir_error(tmp_path):
    """Test error handling in ensure_base_dir."""
    # Create a file where a directory should be
    file_path = tmp_path / "not_a_dir"
    file_path.touch()

    # In some OS/Python versions this might raise differently, but let's see.
    # Actually os.makedirs(..., exist_ok=True) raises OSError if path exists and is not a dir.
    with pytest.raises(OSError):
        exporter.ensure_base_dir(str(file_path))


def test_write_data_file_empty():
    """Test writing data file with empty records (should do nothing)."""
    with patch("builtins.open") as mock_open:
        exporter.write_data_file([], "path", "posts", "CSV")
        mock_open.assert_not_called()
