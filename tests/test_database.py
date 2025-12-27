import sqlite3
import pytest
from database import crud, db_setup, stats_queries
import os
from unittest.mock import MagicMock


@pytest.fixture
def db_conn(tmp_path):
    """Fixture to provide a clean database connection using a temporary file."""
    db_file = tmp_path / "test_insights.db"
    db_setup.init_db(str(db_file))
    conn = crud.get_db_connection(str(db_file))
    assert conn is not None
    yield conn
    conn.close()


def test_init_db(tmp_path):
    """Test database initialization and table creation."""
    db_file = tmp_path / "init_test.db"
    db_setup.init_db(str(db_file))

    assert os.path.exists(db_file)

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "Groups" in tables
    assert "Posts" in tables
    assert "Comments" in tables
    conn.close()


def test_add_group(db_conn):
    """Test adding a new group."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None

    group = crud.get_group_by_id(db_conn, group_id)
    assert group is not None
    assert group["group_name"] == "Test Group"
    assert group["group_url"] == "https://fb.com/groups/test"


def test_add_group_duplicate(db_conn):
    """Test that duplicate groups are handled gracefully (should fail due to UNIQUE constraint)."""
    crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is None


def test_get_group_by_name_and_url(db_conn):
    """Test retrieving groups by name and URL."""
    crud.add_group(db_conn, "Named Group", "https://fb.com/groups/named")

    group_by_name = crud.get_group_by_name(db_conn, "Named Group")
    assert group_by_name is not None
    assert group_by_name["group_url"] == "https://fb.com/groups/named"

    group_by_url = crud.get_group_by_url(db_conn, "https://fb.com/groups/named")
    assert group_by_url is not None
    assert group_by_url["group_name"] == "Named Group"


def test_list_groups(db_conn):
    """Test listing all groups."""
    crud.add_group(db_conn, "Group A", "https://fb.com/groups/a")
    crud.add_group(db_conn, "Group B", "https://fb.com/groups/b")

    groups = crud.list_groups(db_conn)
    assert len(groups) == 2
    assert groups[0]["group_name"] == "Group A"
    assert groups[1]["group_name"] == "Group B"


def test_add_scraped_post(db_conn):
    """Test adding a scraped post."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    post_data = {
        "facebook_post_id": "fb_123",
        "post_url": "https://fb.com/posts/123",
        "content_text": "Hello world",
        "posted_at": "2023-01-01 12:00:00",
        "post_author_name": "Author",
        "post_author_profile_pic_url": "http://pic.com",
        "post_image_url": "http://img.com",
    }

    post_id = crud.add_scraped_post(db_conn, post_data, group_id)
    assert post_id is not None

    # Test duplicate ignore and return existing ID
    post_id_duplicate = crud.add_scraped_post(db_conn, post_data, group_id)
    assert post_id_duplicate == post_id


def test_update_post_with_ai_results(db_conn):
    """Test updating a post with AI results."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    post_id = crud.add_scraped_post(db_conn, {"post_url": "url1", "content_text": "text"}, group_id)
    assert post_id is not None

    ai_data = {
        "ai_category": "Idea",
        "ai_sub_category": "Tech",
        "ai_keywords": ["keyword1", "keyword2"],
        "ai_summary": "Summary",
        "ai_is_potential_idea": True,
        "ai_reasoning": "Reason",
        "ai_raw_response": {"raw": "data"},
    }

    crud.update_post_with_ai_results(db_conn, post_id, ai_data)

    posts = crud.get_all_categorized_posts(db_conn, group_id, {})
    assert len(posts) == 1
    assert posts[0]["ai_category"] == "Idea"
    assert posts[0]["ai_is_potential_idea"] is True
    assert posts[0]["ai_keywords"] == ["keyword1", "keyword2"]


def test_get_unprocessed_posts(db_conn):
    """Test retrieving unprocessed posts."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    crud.add_scraped_post(db_conn, {"post_url": "url1", "content_text": "text1"}, group_id)
    crud.add_scraped_post(db_conn, {"post_url": "url2", "content_text": "text2"}, group_id)

    unprocessed = crud.get_unprocessed_posts(db_conn, group_id)
    assert len(unprocessed) == 2

    # Process one
    internal_id = unprocessed[0]["internal_post_id"]
    crud.update_post_with_ai_results(db_conn, internal_id, {"ai_category": "Cat"})

    unprocessed_after = crud.get_unprocessed_posts(db_conn, group_id)
    assert len(unprocessed_after) == 1
    assert unprocessed_after[0]["post_content_raw"] == "text2"


def test_add_comments_for_post(db_conn):
    """Test adding and retrieving comments."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    post_id = crud.add_scraped_post(db_conn, {"post_url": "url1"}, group_id)
    assert post_id is not None

    comments = [
        {"commenterName": "User1", "commentText": "Comment 1", "commentFacebookId": "cfb_1"},
        {"commenterName": "User2", "commentText": "Comment 2", "commentFacebookId": "cfb_2"},
    ]

    success = crud.add_comments_for_post(db_conn, post_id, comments)
    assert success is True

    retrieved = crud.get_comments_for_post(db_conn, post_id)
    assert len(retrieved) == 2
    assert retrieved[0]["commenter_name"] == "User1"
    assert retrieved[1]["comment_text"] == "Comment 2"


def test_remove_group_cascade(db_conn):
    """Test that removing a group removes associated posts and comments."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    post_id = crud.add_scraped_post(db_conn, {"post_url": "url1"}, group_id)
    assert post_id is not None
    crud.add_comments_for_post(
        db_conn,
        post_id,
        [{"commenterName": "U1", "commentText": "C1", "commentFacebookId": "cfb1"}],
    )

    # Process them
    crud.update_post_with_ai_results(db_conn, post_id, {"ai_category": "Cat"})
    assert len(crud.get_all_categorized_posts(db_conn, group_id, {})) == 1
    assert len(crud.get_comments_for_post(db_conn, post_id)) == 1

    # Remove group
    success = crud.remove_group(db_conn, group_id)
    assert success is True

    # Verify deletion
    assert crud.get_group_by_id(db_conn, group_id) is None

    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Posts WHERE group_id = ?", (group_id,))
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT COUNT(*) FROM Comments WHERE internal_post_id = ?", (post_id,))
    assert cursor.fetchone()[0] == 0


def test_statistics(db_conn):
    """Test statistics queries."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    p1 = crud.add_scraped_post(db_conn, {"post_url": "u1", "post_author_name": "Author1"}, group_id)
    p2 = crud.add_scraped_post(db_conn, {"post_url": "u2", "post_author_name": "Author1"}, group_id)
    p3 = crud.add_scraped_post(db_conn, {"post_url": "u3", "post_author_name": "Author2"}, group_id)

    assert p1 is not None and p2 is not None and p3 is not None

    crud.update_post_with_ai_results(db_conn, p1, {"ai_category": "CategoryA"})
    crud.update_post_with_ai_results(db_conn, p2, {"ai_category": "CategoryA"})
    crud.update_post_with_ai_results(db_conn, p3, {"ai_category": "CategoryB"})

    crud.add_comments_for_post(
        db_conn, p1, [{"commentFacebookId": "c1"}, {"commentFacebookId": "c2"}]
    )
    crud.add_comments_for_post(db_conn, p2, [{"commentFacebookId": "c3"}])

    stats = stats_queries.get_all_statistics(db_conn)
    assert stats["total_posts"] == 3
    assert stats["total_comments"] == 3
    assert stats["unprocessed_posts"] == 0
    assert stats["avg_comments_per_post"] == 1.5

    assert len(stats["posts_per_category"]) == 2
    assert stats["top_authors"][0][0] == "Author1"
    assert stats["top_authors"][0][1] == 2


def test_get_distinct_values(db_conn):
    """Test get_distinct_values with allowed and disallowed fields."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    p1 = crud.add_scraped_post(db_conn, {"post_url": "u1", "post_author_name": "Author1"}, group_id)
    assert p1 is not None
    crud.update_post_with_ai_results(db_conn, p1, {"ai_category": "Cat1"})

    assert crud.get_distinct_values(db_conn, "ai_category") == ["Cat1"]
    assert crud.get_distinct_values(db_conn, "post_author_name") == ["Author1"]
    # Disallowed field
    assert crud.get_distinct_values(db_conn, "post_content_raw") == []


def test_get_all_categorized_posts_filters(db_conn):
    """Test get_all_categorized_posts with various filters."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    p1 = crud.add_scraped_post(
        db_conn, {"post_url": "u1", "content_text": "keyword1", "posted_at": 1000}, group_id
    )
    p2 = crud.add_scraped_post(
        db_conn, {"post_url": "u2", "content_text": "keyword2", "posted_at": 2000}, group_id
    )

    assert p1 is not None and p2 is not None

    crud.update_post_with_ai_results(
        db_conn, p1, {"ai_category": "Cat1", "ai_is_potential_idea": True}
    )
    crud.update_post_with_ai_results(
        db_conn, p2, {"ai_category": "Cat2", "ai_is_potential_idea": False}
    )

    # Filter by idea
    ideas = crud.get_all_categorized_posts(db_conn, group_id, {"is_idea": True})
    assert len(ideas) == 1
    assert ideas[0]["internal_post_id"] == p1

    # Filter by keyword
    kw_results = crud.get_all_categorized_posts(db_conn, group_id, {"keyword": "keyword2"})
    assert len(kw_results) == 1
    assert kw_results[0]["internal_post_id"] == p2

    # Filter by date range
    date_results = crud.get_all_categorized_posts(db_conn, group_id, {"start_date": 1500})
    assert len(date_results) == 1
    assert date_results[0]["internal_post_id"] == p2


def test_add_comments_empty(db_conn):
    """Test adding empty comments list."""
    success = crud.add_comments_for_post(db_conn, 1, [])
    assert success is True


def test_get_all_categorized_posts_complex_filters(db_conn):
    """Test get_all_categorized_posts with complex combinations of filters."""
    group_id = crud.add_group(db_conn, "G1", "U1")
    assert group_id is not None
    p1 = crud.add_scraped_post(
        db_conn, {"post_url": "u1", "post_author_name": "Alice", "posted_at": 100}, group_id
    )
    p2 = crud.add_scraped_post(
        db_conn, {"post_url": "u2", "post_author_name": "Bob", "posted_at": 200}, group_id
    )

    assert p1 is not None and p2 is not None

    crud.update_post_with_ai_results(db_conn, p1, {"ai_category": "Cat1"})
    crud.update_post_with_ai_results(db_conn, p2, {"ai_category": "Cat2"})

    crud.add_comments_for_post(
        db_conn,
        p1,
        [
            {"commenterName": "Charlie", "commentText": "Nice", "commentFacebookId": "c1"},
            {"commenterName": "Dave", "commentText": "Cool", "commentFacebookId": "c2"},
        ],
    )

    # 1. Filter by end_date
    res = crud.get_all_categorized_posts(db_conn, group_id, {"end_date": 150})
    assert len(res) == 1
    assert res[0]["internal_post_id"] == p1

    # 2. Filter by post_author
    res = crud.get_all_categorized_posts(db_conn, group_id, {"post_author": "Alic"})
    assert len(res) == 1
    assert res[0]["post_author_name"] == "Alice"

    # 3. Filter by comment_author
    res = crud.get_all_categorized_posts(db_conn, group_id, {"comment_author": "Char"})
    assert len(res) == 1
    assert res[0]["internal_post_id"] == p1

    # 4. Filter by min_comments
    res = crud.get_all_categorized_posts(db_conn, group_id, {"min_comments": 2})
    assert len(res) == 1
    assert res[0]["comment_count"] == 2

    # 5. Filter by max_comments
    res = crud.get_all_categorized_posts(db_conn, group_id, {"max_comments": 1})
    assert len(res) == 1
    assert res[0]["internal_post_id"] == p2

    # 6. Filter with limit
    res = crud.get_all_categorized_posts(db_conn, group_id, {"limit": 1})
    assert len(res) == 1

    # 7. Filter with no group_id and no filters (all processed posts)
    res = crud.get_all_categorized_posts(db_conn, None, {})
    assert len(res) == 2


def test_get_all_categorized_posts_invalid_boolean(db_conn):
    """Test get_all_categorized_posts with invalid boolean filter value."""
    # This triggers lines 284-289 in crud.py
    res = crud.get_all_categorized_posts(
        db_conn, None, {}, filter_field="ai_is_potential_idea", filter_value="invalid"
    )
    # It should log an error and proceed without that filter
    assert isinstance(res, list)


def test_json_decode_errors(db_conn):
    """Test handling of malformed JSON in database fields."""
    group_id = crud.add_group(db_conn, "G1", "U1")
    assert group_id is not None
    # Manually insert malformed JSON
    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO Posts (group_id, post_url, ai_keywords, ai_raw_response, is_processed_by_ai)
        VALUES (?, ?, ?, ?, 1)
    """,
        (group_id, "bad_json", "not json", "not json"),
    )
    db_conn.commit()
    res = crud.get_all_categorized_posts(db_conn, group_id, {})
    assert len(res) == 1
    assert res[0]["ai_keywords"] == []  # Fallback value


def test_stats_error_handling():
    """Test error handling in statistics queries with a closed connection."""
    conn = sqlite3.connect(":memory:")
    conn.close()

    assert stats_queries.get_total_posts(conn) == 0
    assert stats_queries.get_posts_per_category(conn) == []
    assert stats_queries.get_unprocessed_posts_count(conn) == 0
    assert stats_queries.get_total_comments(conn) == 0
    assert stats_queries.get_avg_comments_per_post(conn) == 0.0
    assert stats_queries.get_top_authors(conn) == []

    stats = stats_queries.get_all_statistics(conn)
    assert stats["total_posts"] == 0
    assert stats["total_comments"] == 0


def test_init_db_error(tmp_path):
    """Test init_db with an invalid path to trigger error handling."""
    # Using a directory name as a file path should trigger a sqlite3.Error
    invalid_path = tmp_path / "invalid_dir"
    invalid_path.mkdir()

    # This should log an error and not raise an exception
    db_setup.init_db(str(invalid_path))


def test_crud_error_handling():
    """Test error handling in CRUD functions using mocks."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_conn.cursor.side_effect = sqlite3.Error("Mocked error")

    assert crud.add_group(mock_conn, "Name", "Url") is None
    assert crud.get_group_by_id(mock_conn, 1) is None
    assert crud.add_scraped_post(mock_conn, {}, 1) is None
    assert crud.get_unprocessed_posts(mock_conn, 1) == []
    assert crud.get_distinct_values(mock_conn, "ai_category") == []
    assert crud.get_all_categorized_posts(mock_conn, 1, {}) == []
    assert crud.get_comments_for_post(mock_conn, 1) == []
    assert crud.get_unprocessed_comments(mock_conn) == []
    assert crud.list_groups(mock_conn) == []
    assert crud.remove_group(mock_conn, 1) is False


def test_get_unprocessed_comments(db_conn):
    """Test retrieving unprocessed comments."""
    group_id = crud.add_group(db_conn, "Test Group", "https://fb.com/groups/test")
    assert group_id is not None
    post_id = crud.add_scraped_post(db_conn, {"post_url": "url1"}, group_id)
    assert post_id is not None
    crud.add_comments_for_post(
        db_conn, post_id, [{"commentText": "C1", "commentFacebookId": "cfb1"}]
    )

    unprocessed = crud.get_unprocessed_comments(db_conn)
    assert len(unprocessed) == 1
    assert unprocessed[0]["comment_text"] == "C1"

    # Update one
    crud.update_comment_with_ai_results(
        db_conn, unprocessed[0]["comment_id"], {"ai_comment_category": "Cat"}
    )

    unprocessed_after = crud.get_unprocessed_comments(db_conn)
    assert len(unprocessed_after) == 0
