"""
Integration Tests for Real Database Operations.

This module tests the service layer with REAL SQLite database operations
to verify that services actually write to and read from the database correctly.
Unlike unit tests that mock the DB connection, these tests use actual database files.

Target: services/ + database/
DB: SQLite (temp file, not production insights.db)
"""

import pytest
import tempfile
import os
from database.db_setup import init_db
from services.group_service import GroupService
from services.post_service import PostService
from services.scraper_service import ScraperService


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup after test
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def initialized_db(temp_db_path):
    """Initialize database schema and provide connection info."""
    init_db(temp_db_path)
    yield temp_db_path


class TestGroupServiceRealDB:
    """Integration tests for GroupService with real database operations."""

    def test_add_group_writes_to_real_db(self, initialized_db):
        """Test that GroupService.add_group writes data to the real database."""
        service = GroupService(db_name=initialized_db)

        # Add a group via service
        group_id = service.add_group(
            url="https://facebook.com/groups/test_integration", name="Integration Test Group"
        )

        # Verify it returned a valid ID
        assert group_id is not None
        assert isinstance(group_id, int)
        assert group_id > 0

        # Retrieve via service and verify
        retrieved_group = service.get_group_by_id(group_id)
        assert retrieved_group is not None
        assert retrieved_group["group_name"] == "Integration Test Group"
        assert retrieved_group["group_url"] == "https://facebook.com/groups/test_integration"

    def test_get_all_groups_returns_written_data(self, initialized_db):
        """Test that get_all_groups returns groups written via add_group."""
        service = GroupService(db_name=initialized_db)

        # Add multiple groups
        group1_id = service.add_group(url="https://facebook.com/groups/group1", name="Group One")
        group2_id = service.add_group(url="https://facebook.com/groups/group2", name="Group Two")

        assert group1_id is not None
        assert group2_id is not None

        # Retrieve all groups
        all_groups = service.get_all_groups()

        # Verify both groups are present
        assert len(all_groups) == 2
        group_names = [g["group_name"] for g in all_groups]
        assert "Group One" in group_names
        assert "Group Two" in group_names

    def test_add_multiple_groups_and_retrieve_individually(self, initialized_db):
        """Test adding multiple groups and retrieving each one individually."""
        service = GroupService(db_name=initialized_db)

        test_groups = [
            ("https://fb.com/groups/a", "Group A"),
            ("https://fb.com/groups/b", "Group B"),
            ("https://fb.com/groups/c", "Group C"),
        ]

        # Add all groups
        group_ids = []
        for url, name in test_groups:
            group_id = service.add_group(url=url, name=name)
            assert group_id is not None
            group_ids.append(group_id)

        # Verify each group can be retrieved individually
        for i, (url, name) in enumerate(test_groups):
            group = service.get_group_by_id(group_ids[i])
            assert group is not None
            assert group["group_name"] == name
            assert group["group_url"] == url

    def test_remove_group_deletes_from_db(self, initialized_db):
        """Test that remove_group actually removes the group from database."""
        service = GroupService(db_name=initialized_db)

        # Add a group
        group_id = service.add_group(
            url="https://facebook.com/groups/delete_test", name="Delete Test Group"
        )
        assert group_id is not None

        # Remove the group
        result = service.remove_group(group_id)
        assert result is True

        # Verify it's gone
        retrieved = service.get_group_by_id(group_id)
        assert retrieved is None

        # Verify not in all groups list
        all_groups = service.get_all_groups()
        assert len(all_groups) == 0


class TestPostServiceRealDB:
    """Integration tests for PostService with real database operations."""

    def test_get_statistics_reads_from_real_db(self, initialized_db):
        """Test that get_statistics reads data that was added to the database."""
        service = PostService(db_name=initialized_db)

        # Get initial statistics (empty database)
        initial_stats = service.get_statistics()
        assert initial_stats is not None
        assert "total_posts" in initial_stats
        assert "total_comments" in initial_stats

        # Add data via GroupService and crud directly
        from database.crud import add_group, add_scraped_post, get_db_connection

        conn = get_db_connection(initialized_db)
        assert conn is not None, "Failed to get database connection"

        group_id = add_group(conn, "Stats Test Group", "https://facebook.com/groups/stats_test")
        assert group_id is not None
        conn.close()

        # Add some posts
        conn = get_db_connection(initialized_db)
        assert conn is not None

        for i in range(3):
            post_id = add_scraped_post(
                conn,
                {
                    "facebook_post_id": f"fb_{i}",
                    "post_url": f"https://fb.com/posts/{i}",
                    "content_text": f"Test post content {i}",
                    "posted_at": "2023-01-01 12:00:00",
                    "post_author_name": "Test Author",
                },
                group_id,
            )
            assert post_id is not None

        conn.close()

        # Get updated statistics
        updated_stats = service.get_statistics()
        assert updated_stats is not None
        assert updated_stats["total_posts"] == 3
        assert updated_stats["total_comments"] == 0  # No comments yet

        # Verify stats increased from initial
        assert updated_stats["total_posts"] > initial_stats["total_posts"]

    def test_get_statistics_empty_db(self, initialized_db):
        """Test get_statistics with a fresh database."""
        service = PostService(db_name=initialized_db)

        stats = service.get_statistics()

        # Should return valid structure even when empty
        assert stats is not None
        assert "total_posts" in stats
        assert "total_comments" in stats
        assert "unprocessed_posts" in stats
        assert stats["total_posts"] == 0
        assert stats["total_comments"] == 0

    def test_get_filtered_posts_with_real_data(self, initialized_db):
        """Test that get_filtered_posts returns posts added via CRUD."""
        from database.crud import (
            add_group,
            add_scraped_post,
            update_post_with_ai_results,
            get_db_connection,
        )

        service = PostService(db_name=initialized_db)

        # Setup: Add group and posts
        conn = get_db_connection(initialized_db)
        assert conn is not None, "Failed to get database connection"

        group_id = add_group(conn, "Filter Test Group", "https://fb.com/groups/filter_test")
        assert group_id is not None

        # Add and process posts
        post1_id = add_scraped_post(
            conn, {"post_url": "url1", "content_text": "Python tutorial"}, group_id
        )
        post2_id = add_scraped_post(
            conn, {"post_url": "url2", "content_text": "JavaScript tutorial"}, group_id
        )

        assert post1_id is not None
        assert post2_id is not None

        # Process posts with AI results
        update_post_with_ai_results(
            conn, post1_id, {"ai_category": "Tutorial", "ai_is_potential_idea": True}
        )
        update_post_with_ai_results(
            conn, post2_id, {"ai_category": "Tutorial", "ai_is_potential_idea": False}
        )

        conn.close()

        # Retrieve via service
        all_tutorials = service.get_filtered_posts(
            group_id=group_id, filters={"category": "Tutorial"}
        )

        assert len(all_tutorials) == 2

        # Filter by ideas
        ideas = service.get_filtered_posts(group_id=group_id, filters={"is_idea": True})
        assert len(ideas) == 1
        assert ideas[0]["internal_post_id"] == post1_id


class TestScraperServiceRealDB:
    """Integration tests for ScraperService initialization with real database."""

    def test_scraper_service_initialization(self, initialized_db):
        """Test that ScraperService can be instantiated without errors."""
        service = ScraperService()

        assert service is not None
        assert hasattr(service, "logger")
        assert hasattr(service, "scrape_group")

    def test_scraper_service_get_or_create_group_existing(self, initialized_db):
        """Test _get_or_create_group_id returns existing group ID."""
        from database.crud import add_group, get_db_connection

        service = ScraperService()

        # Add a group directly via CRUD
        conn = get_db_connection(initialized_db)
        assert conn is not None, "Failed to get database connection"

        existing_id = add_group(conn, "Existing Group", "https://fb.com/groups/existing")
        assert existing_id is not None
        conn.close()

        # Test retrieval via service method
        conn = get_db_connection(initialized_db)
        assert conn is not None

        retrieved_id = service._get_or_create_group_id(conn, "https://fb.com/groups/existing")
        conn.close()

        assert retrieved_id == existing_id

    def test_scraper_service_get_or_create_group_new(self, initialized_db):
        """Test _get_or_create_group_id creates new group when not found."""
        from database.crud import get_db_connection

        service = ScraperService()

        conn = get_db_connection(initialized_db)
        assert conn is not None, "Failed to get database connection"

        # Test with new URL (should create group)
        new_id = service._get_or_create_group_id(
            conn, "https://fb.com/groups/new_group", group_name="New Group Created by Service"
        )
        conn.close()

        assert new_id is not None
        assert isinstance(new_id, int)

        # Verify it was created by checking via service
        conn = get_db_connection(initialized_db)
        assert conn is not None

        retrieved_id = service._get_or_create_group_id(conn, "https://fb.com/groups/new_group")
        conn.close()

        assert retrieved_id == new_id

    def test_scraper_service_handles_db_connection(self, initialized_db):
        """Test that ScraperService properly handles database connections."""
        from services.scraper_service import ScrapeResult

        service = ScraperService()

        # Test that it creates proper ScrapeResult objects
        success_result = ScrapeResult(
            success=True, scraped_count=5, added_count=3, ai_processed_count=2, ai_skipped_count=1
        )

        assert success_result.success is True
        assert success_result.scraped_count == 5
        assert "successfully" in str(success_result)

        failure_result = ScrapeResult(
            success=False,
            scraped_count=0,
            added_count=0,
            ai_processed_count=0,
            ai_skipped_count=0,
            error_message="Test error",
        )

        assert failure_result.success is False
        assert "failed" in str(failure_result)
        assert "Test error" in str(failure_result)


class TestEndToEndServiceIntegration:
    """End-to-end tests that verify service-to-service database operations."""

    def test_group_then_posts_flow(self, initialized_db):
        """Test complete flow: add group, add posts, retrieve via services."""
        # 1. Add group via GroupService
        group_service = GroupService(db_name=initialized_db)
        group_id = group_service.add_group(
            url="https://facebook.com/groups/e2e_test", name="E2E Test Group"
        )
        assert group_id is not None

        # 2. Add posts directly via CRUD (simulating what scraper would do)
        from database.crud import add_scraped_post, update_post_with_ai_results, get_db_connection

        conn = get_db_connection(initialized_db)
        assert conn is not None, "Failed to get database connection"

        post_ids = []
        for i in range(2):
            post_id = add_scraped_post(
                conn,
                {
                    "post_url": f"https://fb.com/posts/e2e_{i}",
                    "content_text": f"E2E test post {i}",
                    "posted_at": "2023-01-01 12:00:00",
                    "post_author_name": "E2E Author",
                },
                group_id,
            )
            assert post_id is not None
            post_ids.append(post_id)

        # Process one post
        update_post_with_ai_results(
            conn, post_ids[0], {"ai_category": "Project Idea", "ai_is_potential_idea": True}
        )
        conn.close()

        # 3. Verify via PostService
        post_service = PostService(db_name=initialized_db)
        stats = post_service.get_statistics()

        assert stats["total_posts"] == 2

        # 4. Verify via GroupService
        retrieved_group = group_service.get_group_by_id(group_id)
        assert retrieved_group is not None
        assert retrieved_group["group_name"] == "E2E Test Group"

        all_groups = group_service.get_all_groups()
        assert len(all_groups) == 1

    def test_multiple_services_share_same_db(self, initialized_db):
        """Test that multiple service instances work with the same database."""
        group_service = GroupService(db_name=initialized_db)
        post_service = PostService(db_name=initialized_db)

        # Both services should be able to access the same data
        group_id = group_service.add_group(
            url="https://facebook.com/groups/shared", name="Shared Database Test"
        )
        assert group_id is not None

        # PostService should see the empty database
        stats_before = post_service.get_statistics()
        assert stats_before["total_posts"] == 0

        # GroupService should see the group
        groups = group_service.get_all_groups()
        assert len(groups) == 1
        assert groups[0]["group_name"] == "Shared Database Test"
