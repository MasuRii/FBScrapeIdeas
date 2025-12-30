"""
Tests for Service Layer Modules.

This module tests the service layer abstractions:
- GroupService: Group management operations
- PostService: Post retrieval and filtering
- ScraperService: Scraper engine selection and orchestration
- AIService: AI provider initialization and batch processing

All tests use mocks to avoid real DB/Network calls.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sqlite3


# =============================================================================
# GroupService Tests
# =============================================================================


class TestGroupService:
    """Test suite for GroupService class."""

    # -------------------------------------------------------------------------
    # Happy Path Tests
    # -------------------------------------------------------------------------

    def test_get_all_groups_success(self):
        """Test successful retrieval of all groups."""
        from services.group_service import GroupService

        mock_groups = [
            {"group_id": 1, "group_name": "Group A", "group_url": "http://fb.com/a"},
            {"group_id": 2, "group_name": "Group B", "group_url": "http://fb.com/b"},
        ]

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("services.group_service.list_groups") as mock_list,
        ):
            mock_conn.return_value = MagicMock()
            mock_list.return_value = mock_groups

            service = GroupService(db_name="test.db")
            result = service.get_all_groups()

            assert result == mock_groups
            assert len(result) == 2
            mock_conn.assert_called_once_with("test.db")
            mock_list.assert_called_once()

    def test_add_group_success(self):
        """Test successful addition of a new group."""
        from services.group_service import GroupService

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("services.group_service.add_group") as mock_add,
        ):
            mock_conn.return_value = MagicMock()
            mock_add.return_value = 42

            service = GroupService(db_name="test.db")
            result = service.add_group(url="https://facebook.com/groups/newgroup", name="New Group")

            assert result == 42
            mock_add.assert_called_once()

    def test_get_group_by_id_success(self):
        """Test successful retrieval of a specific group."""
        from services.group_service import GroupService

        mock_group = {"group_id": 1, "group_name": "Test", "group_url": "http://fb.com/test"}

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("services.group_service.get_group_by_id") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_group

            service = GroupService(db_name="test.db")
            result = service.get_group_by_id(group_id=1)

            assert result == mock_group
            assert result["group_id"] == 1

    def test_remove_group_success(self):
        """Test successful removal of a group."""
        from services.group_service import GroupService

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("database.crud.remove_group") as mock_remove,
        ):
            mock_conn.return_value = MagicMock()
            mock_remove.return_value = True

            service = GroupService(db_name="test.db")
            result = service.remove_group(group_id=1)

            assert result is True

    # -------------------------------------------------------------------------
    # Error Path Tests
    # -------------------------------------------------------------------------

    def test_get_all_groups_db_connection_fails(self):
        """Test handling when database connection fails."""
        from services.group_service import GroupService

        with patch("services.group_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = GroupService(db_name="test.db")
            result = service.get_all_groups()

            assert result == []

    def test_add_group_db_connection_fails(self):
        """Test add_group returns None when DB connection fails."""
        from services.group_service import GroupService

        with patch("services.group_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = GroupService(db_name="test.db")
            result = service.add_group(url="http://fb.com/test", name="Test")

            assert result is None

    def test_get_group_by_id_not_found(self):
        """Test handling when group is not found."""
        from services.group_service import GroupService

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("services.group_service.get_group_by_id") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = None

            service = GroupService(db_name="test.db")
            result = service.get_group_by_id(group_id=999)

            assert result is None

    def test_add_group_exception_handling(self):
        """Test that exceptions are caught and None is returned."""
        from services.group_service import GroupService

        with patch("services.group_service.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Unexpected DB error")

            service = GroupService(db_name="test.db")
            result = service.add_group(url="http://fb.com/test", name="Test")

            assert result is None

    def test_remove_group_db_connection_fails(self):
        """Test remove_group returns False when DB connection fails."""
        from services.group_service import GroupService

        with patch("services.group_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = GroupService(db_name="test.db")
            result = service.remove_group(group_id=1)

            assert result is False

    def test_get_all_groups_exception_handling(self):
        """Test exception handling in get_all_groups."""
        from services.group_service import GroupService

        with patch("services.group_service.get_db_connection") as mock_conn:
            mock_conn.side_effect = sqlite3.Error("Connection lost")

            service = GroupService(db_name="test.db")
            result = service.get_all_groups()

            assert result == []

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_get_all_groups_empty_list(self):
        """Test handling when no groups exist."""
        from services.group_service import GroupService

        with (
            patch("services.group_service.get_db_connection") as mock_conn,
            patch("services.group_service.list_groups") as mock_list,
        ):
            mock_conn.return_value = MagicMock()
            mock_list.return_value = []

            service = GroupService(db_name="test.db")
            result = service.get_all_groups()

            assert result == []


# =============================================================================
# PostService Tests
# =============================================================================


class TestPostService:
    """Test suite for PostService class."""

    # -------------------------------------------------------------------------
    # Happy Path Tests
    # -------------------------------------------------------------------------

    def test_get_filtered_posts_success(self):
        """Test successful retrieval of filtered posts."""
        from services.post_service import PostService

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Test post 1"},
            {"internal_post_id": 2, "post_content_raw": "Test post 2"},
        ]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            result = service.get_filtered_posts(group_id=1)

            assert result == mock_posts
            assert len(result) == 2

    def test_get_filtered_posts_with_filters(self):
        """Test retrieval with various filter criteria."""
        from services.post_service import PostService

        mock_posts = [{"internal_post_id": 1, "ai_category": "Ideas"}]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            filters = {"category": "Ideas", "is_idea": True}
            result = service.get_filtered_posts(group_id=1, filters=filters)

            assert result == mock_posts

    def test_get_filtered_posts_with_limit(self):
        """Test retrieval with limit parameter."""
        from services.post_service import PostService

        mock_posts = [{"internal_post_id": 1}]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            result = service.get_filtered_posts(group_id=1, limit=5)

            assert result == mock_posts
            # Verify limit was included in the call
            call_args = mock_get.call_args
            filters_arg = call_args[0][2]  # Third positional arg is filters
            assert filters_arg.get("limit") == 5

    def test_get_filtered_posts_with_field_value_filters(self):
        """Test retrieval with special field/value filter parameters."""
        from services.post_service import PostService

        mock_posts = [{"internal_post_id": 1, "ai_category": "Tech"}]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            filters = {"field": "ai_category", "value": "Tech"}
            result = service.get_filtered_posts(group_id=1, filters=filters)

            assert result == mock_posts
            # Verify field and value were extracted and passed correctly
            call_args = mock_get.call_args
            # filter_field is 4th positional arg
            assert call_args[0][3] == "ai_category"
            # filter_value is 5th positional arg
            assert call_args[0][4] == "Tech"

    def test_get_post_comments_success(self):
        """Test successful retrieval of comments for a post."""
        from services.post_service import PostService

        mock_comments = [
            {"comment_id": 1, "comment_text": "Comment 1"},
            {"comment_id": 2, "comment_text": "Comment 2"},
        ]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_comments_for_post") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_comments

            service = PostService(db_name="test.db")
            result = service.get_post_comments(internal_post_id=1)

            assert result == mock_comments
            assert len(result) == 2

    def test_get_distinct_filter_values_success(self):
        """Test successful retrieval of distinct filter values."""
        from services.post_service import PostService

        mock_values = ["Category A", "Category B", "Category C"]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_distinct_values") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_values

            service = PostService(db_name="test.db")
            result = service.get_distinct_filter_values(field_name="ai_category")

            assert result == mock_values
            mock_get.assert_called_once()

    def test_get_statistics_success(self):
        """Test successful retrieval of database statistics."""
        from services.post_service import PostService

        mock_stats = {
            "total_posts": 100,
            "total_comments": 500,
            "unprocessed_posts": 10,
        }

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_statistics") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_stats

            service = PostService(db_name="test.db")
            result = service.get_statistics()

            assert result == mock_stats
            assert result["total_posts"] == 100

    # -------------------------------------------------------------------------
    # Error Path Tests
    # -------------------------------------------------------------------------

    def test_get_filtered_posts_db_connection_fails(self):
        """Test handling when database connection fails."""
        from services.post_service import PostService

        with patch("services.post_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = PostService(db_name="test.db")
            result = service.get_filtered_posts(group_id=1)

            assert result == []

    def test_get_post_comments_db_connection_fails(self):
        """Test handling when database connection fails for comments."""
        from services.post_service import PostService

        with patch("services.post_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = PostService(db_name="test.db")
            result = service.get_post_comments(internal_post_id=1)

            assert result == []

    def test_get_statistics_db_connection_fails(self):
        """Test handling when database connection fails for statistics."""
        from services.post_service import PostService

        with patch("services.post_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = PostService(db_name="test.db")
            result = service.get_statistics()

            assert result == {}

    def test_get_filtered_posts_exception_handling(self):
        """Test exception handling in get_filtered_posts."""
        from services.post_service import PostService

        with patch("services.post_service.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database error")

            service = PostService(db_name="test.db")
            result = service.get_filtered_posts(group_id=1)

            assert result == []

    def test_get_distinct_filter_values_exception_handling(self):
        """Test exception handling in get_distinct_filter_values."""
        from services.post_service import PostService

        with patch("services.post_service.get_db_connection") as mock_conn:
            mock_conn.return_value = MagicMock()
            mock_conn.return_value.close.side_effect = Exception("Close error")

            with patch("services.post_service.get_distinct_values") as mock_get:
                mock_get.side_effect = Exception("Query error")

                service = PostService(db_name="test.db")
                result = service.get_distinct_filter_values(field_name="ai_category")

                assert result == []

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_get_filtered_posts_none_filters(self):
        """Test handling when filters is None."""
        from services.post_service import PostService

        mock_posts = [{"internal_post_id": 1}]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            # Pass filters=None explicitly
            result = service.get_filtered_posts(group_id=1, filters=None)

            assert result == mock_posts

    def test_get_filtered_posts_empty_filters(self):
        """Test handling when filters is an empty dict."""
        from services.post_service import PostService

        mock_posts = [{"internal_post_id": 1}]

        with (
            patch("services.post_service.get_db_connection") as mock_conn,
            patch("services.post_service.get_all_categorized_posts") as mock_get,
        ):
            mock_conn.return_value = MagicMock()
            mock_get.return_value = mock_posts

            service = PostService(db_name="test.db")
            result = service.get_filtered_posts(group_id=1, filters={})

            assert result == mock_posts


# =============================================================================
# ScraperService Tests
# =============================================================================


class TestScraperService:
    """Test suite for ScraperService class."""

    # -------------------------------------------------------------------------
    # Engine Selection Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scrape_group_invalid_engine_raises_value_error(self):
        """Test that invalid engine raises ValueError."""
        from services.scraper_service import ScraperService

        service = ScraperService()

        with pytest.raises(ValueError) as exc_info:
            await service.scrape_group(
                group_url="https://facebook.com/groups/test", post_count=10, engine="invalid_engine"
            )

        assert "Invalid engine" in str(exc_info.value)
        assert "invalid_engine" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scrape_group_selects_playwright_engine(self):
        """Test that playwright engine is correctly selected."""
        from services.scraper_service import ScraperService, ScrapeResult

        with (
            patch("services.scraper_service.get_db_connection") as mock_conn,
            patch("services.scraper_service.get_scraper_engine") as mock_engine,
            patch.object(
                ScraperService, "_scrape_with_playwright", new_callable=AsyncMock
            ) as mock_scrape,
        ):
            mock_conn.return_value = MagicMock()
            mock_engine.return_value = "playwright"
            mock_scrape.return_value = ScrapeResult(
                success=True,
                scraped_count=5,
                added_count=5,
                ai_processed_count=5,
                ai_skipped_count=0,
            )

            # Mock _get_or_create_group_id to return a valid group_id
            with patch.object(ScraperService, "_get_or_create_group_id", return_value=1):
                service = ScraperService()
                result = await service.scrape_group(
                    group_url="https://facebook.com/groups/test", post_count=10, engine="playwright"
                )

                assert result.success is True
                mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_group_selects_selenium_engine(self):
        """Test that selenium engine is correctly selected."""
        from services.scraper_service import ScraperService, ScrapeResult

        with (
            patch("services.scraper_service.get_db_connection") as mock_conn,
            patch.object(
                ScraperService, "_scrape_with_selenium", new_callable=AsyncMock
            ) as mock_scrape,
        ):
            mock_conn.return_value = MagicMock()
            mock_scrape.return_value = ScrapeResult(
                success=True,
                scraped_count=5,
                added_count=5,
                ai_processed_count=5,
                ai_skipped_count=0,
            )

            with patch.object(ScraperService, "_get_or_create_group_id", return_value=1):
                service = ScraperService()
                result = await service.scrape_group(
                    group_url="https://facebook.com/groups/test", post_count=10, engine="selenium"
                )

                assert result.success is True
                mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_group_uses_default_engine_from_config(self):
        """Test that default engine from config is used when not specified."""
        from services.scraper_service import ScraperService, ScrapeResult

        with (
            patch("services.scraper_service.get_db_connection") as mock_conn,
            patch("services.scraper_service.get_scraper_engine") as mock_engine,
            patch.object(
                ScraperService, "_scrape_with_selenium", new_callable=AsyncMock
            ) as mock_scrape,
        ):
            mock_conn.return_value = MagicMock()
            mock_engine.return_value = "selenium"
            mock_scrape.return_value = ScrapeResult(
                success=True,
                scraped_count=5,
                added_count=5,
                ai_processed_count=5,
                ai_skipped_count=0,
            )

            with patch.object(ScraperService, "_get_or_create_group_id", return_value=1):
                service = ScraperService()
                # Don't specify engine - should use default from config
                result = await service.scrape_group(
                    group_url="https://facebook.com/groups/test", post_count=10
                )

                assert result.success is True
                mock_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_group_engine_case_insensitive(self):
        """Test that engine name is case-insensitive."""
        from services.scraper_service import ScraperService, ScrapeResult

        with (
            patch("services.scraper_service.get_db_connection") as mock_conn,
            patch.object(
                ScraperService, "_scrape_with_playwright", new_callable=AsyncMock
            ) as mock_scrape,
        ):
            mock_conn.return_value = MagicMock()
            mock_scrape.return_value = ScrapeResult(
                success=True,
                scraped_count=5,
                added_count=5,
                ai_processed_count=5,
                ai_skipped_count=0,
            )

            with patch.object(ScraperService, "_get_or_create_group_id", return_value=1):
                service = ScraperService()
                # Use uppercase engine name
                result = await service.scrape_group(
                    group_url="https://facebook.com/groups/test", post_count=10, engine="PLAYWRIGHT"
                )

                assert result.success is True
                mock_scrape.assert_called_once()

    # -------------------------------------------------------------------------
    # Database Connection Error Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scrape_group_db_connection_fails(self):
        """Test handling when database connection fails."""
        from services.scraper_service import ScraperService

        with patch("services.scraper_service.get_db_connection") as mock_conn:
            mock_conn.return_value = None

            service = ScraperService()
            result = await service.scrape_group(
                group_url="https://facebook.com/groups/test", post_count=10, engine="selenium"
            )

            assert result.success is False
            assert "database" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_scrape_group_group_id_resolution_fails(self):
        """Test handling when group ID resolution fails."""
        from services.scraper_service import ScraperService

        with patch("services.scraper_service.get_db_connection") as mock_conn:
            mock_conn.return_value = MagicMock()

            with patch.object(ScraperService, "_get_or_create_group_id", return_value=None):
                service = ScraperService()
                result = await service.scrape_group(
                    group_url="https://facebook.com/groups/test", post_count=10, engine="selenium"
                )

                assert result.success is False
                assert "group" in result.error_message.lower()

    # -------------------------------------------------------------------------
    # ScrapeResult Tests
    # -------------------------------------------------------------------------

    def test_scrape_result_success_string(self):
        """Test ScrapeResult string representation for success."""
        from services.scraper_service import ScrapeResult

        result = ScrapeResult(
            success=True, scraped_count=10, added_count=8, ai_processed_count=7, ai_skipped_count=1
        )

        result_str = str(result)
        assert "successfully" in result_str
        assert "10" in result_str
        assert "8" in result_str

    def test_scrape_result_failure_string(self):
        """Test ScrapeResult string representation for failure."""
        from services.scraper_service import ScrapeResult

        result = ScrapeResult(
            success=False,
            scraped_count=0,
            added_count=0,
            ai_processed_count=0,
            ai_skipped_count=0,
            error_message="Connection timeout",
        )

        result_str = str(result)
        assert "failed" in result_str
        assert "Connection timeout" in result_str

    # -------------------------------------------------------------------------
    # _get_or_create_group_id Tests
    # -------------------------------------------------------------------------

    def test_get_or_create_group_id_existing(self):
        """Test that existing group ID is returned."""
        from services.scraper_service import ScraperService

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value = mock_cursor

        service = ScraperService()
        result = service._get_or_create_group_id(
            conn=mock_conn, group_url="https://facebook.com/groups/existing"
        )

        assert result == 42
        # Verify only SELECT was called, no INSERT
        mock_cursor.execute.assert_called_once()
        assert "SELECT" in mock_cursor.execute.call_args[0][0]

    def test_get_or_create_group_id_creates_new(self):
        """Test that new group is created when not found."""
        from services.scraper_service import ScraperService

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call returns None (not found), second is the insert
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 99
        mock_conn.cursor.return_value = mock_cursor

        service = ScraperService()
        result = service._get_or_create_group_id(
            conn=mock_conn, group_url="https://facebook.com/groups/new"
        )

        assert result == 99
        # Verify INSERT was called
        calls = mock_cursor.execute.call_args_list
        assert any("INSERT" in call[0][0] for call in calls)

    def test_get_or_create_group_id_with_custom_name(self):
        """Test that custom group name is used when provided."""
        from services.scraper_service import ScraperService

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 100
        mock_conn.cursor.return_value = mock_cursor

        service = ScraperService()
        result = service._get_or_create_group_id(
            conn=mock_conn,
            group_url="https://facebook.com/groups/new",
            group_name="Custom Group Name",
        )

        assert result == 100
        # Verify custom name was used in INSERT
        insert_call = [c for c in mock_cursor.execute.call_args_list if "INSERT" in c[0][0]][0]
        assert "Custom Group Name" in insert_call[0][1]

    def test_get_or_create_group_id_db_error(self):
        """Test handling of database errors."""
        from services.scraper_service import ScraperService

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = sqlite3.Error("DB Error")

        service = ScraperService()
        result = service._get_or_create_group_id(
            conn=mock_conn, group_url="https://facebook.com/groups/test"
        )

        assert result is None


# =============================================================================
# AIService Tests
# =============================================================================


class TestAIService:
    """Test suite for AIService class."""

    # -------------------------------------------------------------------------
    # Provider Initialization Tests
    # -------------------------------------------------------------------------

    def test_get_provider_gemini_success(self):
        """Test successful Gemini provider initialization."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with patch("services.ai_service.get_ai_provider") as mock_factory:
            mock_factory.return_value = mock_provider

            service = AIService(db_name="test.db")
            provider = service._get_provider(provider_type="gemini")

            assert provider == mock_provider
            mock_factory.assert_called_once_with(provider_type="gemini")

    def test_get_provider_openai_success(self):
        """Test successful OpenAI provider initialization."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "OpenAI"
        mock_provider.get_model_name.return_value = "gpt-4o-mini"

        with patch("services.ai_service.get_ai_provider") as mock_factory:
            mock_factory.return_value = mock_provider

            service = AIService(db_name="test.db")
            provider = service._get_provider(provider_type="openai")

            assert provider == mock_provider
            mock_factory.assert_called_once_with(provider_type="openai")

    def test_get_provider_caches_instance(self):
        """Test that provider is cached after first initialization."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with patch("services.ai_service.get_ai_provider") as mock_factory:
            mock_factory.return_value = mock_provider

            service = AIService(db_name="test.db")
            # First call
            provider1 = service._get_provider(provider_type="gemini")
            # Second call
            provider2 = service._get_provider(provider_type="gemini")

            # Factory should only be called once
            mock_factory.assert_called_once()
            assert provider1 is provider2

    def test_get_provider_initialization_failure(self):
        """Test handling of provider initialization failure."""
        from services.ai_service import AIService

        with patch("services.ai_service.get_ai_provider") as mock_factory:
            mock_factory.side_effect = ValueError("Missing API key")

            service = AIService(db_name="test.db")

            with pytest.raises(ValueError) as exc_info:
                service._get_provider(provider_type="gemini")

            assert "initialization failed" in str(exc_info.value).lower()

    def test_get_provider_uses_default_from_config(self):
        """Test that default provider from config is used when not specified."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with patch("services.ai_service.get_ai_provider") as mock_factory:
            mock_factory.return_value = mock_provider

            service = AIService(db_name="test.db")
            # Don't specify provider_type
            provider = service._get_provider()

            # Factory should be called with provider_type=None (uses default)
            mock_factory.assert_called_once_with(provider_type=None)

    # -------------------------------------------------------------------------
    # process_pending_posts Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_pending_posts_success(self):
        """Test successful processing of pending posts."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_posts_batch = AsyncMock(
            return_value=[
                {"internal_post_id": 1, "ai_category": "Ideas"},
                {"internal_post_id": 2, "ai_category": "Questions"},
            ]
        )

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Post 1"},
            {"internal_post_id": 2, "post_content_raw": "Post 2"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
            patch("services.ai_service.create_post_batches") as mock_batches,
            patch("services.ai_service.update_post_with_ai_results") as mock_update,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = mock_posts
            mock_batches.return_value = [mock_posts]  # One batch with all posts

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts()

            assert result["total_posts"] == 2
            assert result["processed"] == 2
            assert result["batches"] == 1
            assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_process_pending_posts_no_unprocessed(self):
        """Test handling when no unprocessed posts exist."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = []  # No unprocessed posts

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts()

            assert result["total_posts"] == 0
            assert result["processed"] == 0
            assert result["batches"] == 0

    @pytest.mark.asyncio
    async def test_process_pending_posts_with_limit(self):
        """Test that limit parameter restricts number of posts processed."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_posts_batch = AsyncMock(
            return_value=[
                {"internal_post_id": 1, "ai_category": "Ideas"},
            ]
        )

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Post 1"},
            {"internal_post_id": 2, "post_content_raw": "Post 2"},
            {"internal_post_id": 3, "post_content_raw": "Post 3"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
            patch("services.ai_service.create_post_batches") as mock_batches,
            patch("services.ai_service.update_post_with_ai_results"),
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = mock_posts
            # Batches will only include the first post due to limit
            mock_batches.return_value = [[mock_posts[0]]]

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts(limit=1)

            assert result["total_posts"] == 3  # Total found
            # Only 1 processed due to limit
            assert result["processed"] == 1

    @pytest.mark.asyncio
    async def test_process_pending_posts_db_connection_fails(self):
        """Test handling when database connection fails."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = None

            service = AIService(db_name="test.db")

            with pytest.raises(Exception) as exc_info:
                await service.process_pending_posts()

            assert "database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_pending_posts_batch_error_handling(self):
        """Test error handling when a batch fails."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_posts_batch = AsyncMock(side_effect=Exception("API Error"))

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Post 1"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
            patch("services.ai_service.create_post_batches") as mock_batches,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = mock_posts
            mock_batches.return_value = [mock_posts]

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts()

            assert result["errors"] == 1  # Error count should be incremented

    @pytest.mark.asyncio
    async def test_process_pending_posts_missing_internal_post_id(self):
        """Test handling when AI result is missing internal_post_id."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_posts_batch = AsyncMock(
            return_value=[
                {"ai_category": "Ideas"},  # Missing internal_post_id
            ]
        )

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Post 1"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
            patch("services.ai_service.create_post_batches") as mock_batches,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = mock_posts
            mock_batches.return_value = [mock_posts]

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts()

            assert result["errors"] == 1  # Missing ID should be counted as error

    @pytest.mark.asyncio
    async def test_process_pending_posts_with_group_id_filter(self):
        """Test processing posts filtered by group_id."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_posts_batch = AsyncMock(
            return_value=[
                {"internal_post_id": 1, "ai_category": "Ideas"},
            ]
        )

        mock_posts = [
            {"internal_post_id": 1, "post_content_raw": "Post 1"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_posts") as mock_get_posts,
            patch("services.ai_service.create_post_batches") as mock_batches,
            patch("services.ai_service.update_post_with_ai_results"),
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_posts.return_value = mock_posts
            mock_batches.return_value = [mock_posts]

            service = AIService(db_name="test.db")
            result = await service.process_pending_posts(group_id=42)

            # Verify group_id was passed to get_unprocessed_posts
            mock_get_posts.assert_called_once()
            call_args = mock_get_posts.call_args
            assert call_args[0][1] == 42  # Second positional arg is group_id

    # -------------------------------------------------------------------------
    # process_pending_comments Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_pending_comments_success(self):
        """Test successful processing of pending comments."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_comments_batch = MagicMock(
            return_value=[
                {"comment_id": 1, "ai_comment_category": "Feedback"},
                {"comment_id": 2, "ai_comment_category": "Question"},
            ]
        )

        mock_comments = [
            {"comment_id": 1, "comment_text": "Comment 1"},
            {"comment_id": 2, "comment_text": "Comment 2"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_comments") as mock_get_comments,
            patch("services.ai_service.update_comment_with_ai_results") as mock_update,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_comments.return_value = mock_comments

            service = AIService(db_name="test.db")
            result = await service.process_pending_comments()

            assert result["total_comments"] == 2
            assert result["processed"] == 2
            assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_process_pending_comments_no_unprocessed(self):
        """Test handling when no unprocessed comments exist."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_comments") as mock_get_comments,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_comments.return_value = []

            service = AIService(db_name="test.db")
            result = await service.process_pending_comments()

            assert result["total_comments"] == 0
            assert result["processed"] == 0

    @pytest.mark.asyncio
    async def test_process_pending_comments_missing_comment_id(self):
        """Test handling when AI result is missing comment_id."""
        from services.ai_service import AIService

        mock_provider = MagicMock()
        mock_provider.provider_name = "Gemini"
        mock_provider.get_model_name.return_value = "gemini-2.0-flash"
        mock_provider.analyze_comments_batch = MagicMock(
            return_value=[
                {"ai_comment_category": "Feedback"},  # Missing comment_id
            ]
        )

        mock_comments = [
            {"comment_id": 1, "comment_text": "Comment 1"},
        ]

        with (
            patch("services.ai_service.get_ai_provider") as mock_factory,
            patch("services.ai_service.get_db_connection") as mock_conn,
            patch("services.ai_service.get_unprocessed_comments") as mock_get_comments,
        ):
            mock_factory.return_value = mock_provider
            mock_conn.return_value = MagicMock()
            mock_get_comments.return_value = mock_comments

            service = AIService(db_name="test.db")
            result = await service.process_pending_comments()

            assert result["errors"] == 1


# =============================================================================
# Provider Factory Tests (via AIService integration)
# =============================================================================


class TestProviderFactory:
    """Test suite for provider_factory integration."""

    def test_get_ai_provider_gemini(self):
        """Test that Gemini provider is created correctly."""
        from ai.provider_factory import get_ai_provider

        # When provider_type is explicitly passed, _create_gemini_provider is called directly
        with patch("ai.provider_factory._create_gemini_provider") as mock_create:
            mock_create.return_value = MagicMock()

            provider = get_ai_provider(provider_type="gemini")

            mock_create.assert_called_once()

    def test_get_ai_provider_openai(self):
        """Test that OpenAI provider is created correctly."""
        from ai.provider_factory import get_ai_provider

        # When provider_type is explicitly passed, _create_openai_provider is called directly
        with patch("ai.provider_factory._create_openai_provider") as mock_create:
            mock_create.return_value = MagicMock()

            provider = get_ai_provider(provider_type="openai")

            mock_create.assert_called_once()

    def test_get_ai_provider_invalid_type(self):
        """Test that invalid provider type raises ValueError."""
        from ai.provider_factory import get_ai_provider

        with pytest.raises(ValueError) as exc_info:
            get_ai_provider(provider_type="invalid_provider")

        assert "Unknown AI provider type" in str(exc_info.value)

    def test_list_available_providers(self):
        """Test listing available providers."""
        from ai.provider_factory import list_available_providers

        providers = list_available_providers()

        assert "gemini" in providers
        assert "openai" in providers

    def test_get_provider_info_gemini(self):
        """Test getting Gemini provider info."""
        from ai.provider_factory import get_provider_info

        info = get_provider_info("gemini")

        assert info["name"] == "Google Gemini"
        assert "GOOGLE_API_KEY" in info["required_config"]

    def test_get_provider_info_openai(self):
        """Test getting OpenAI provider info."""
        from ai.provider_factory import get_provider_info

        info = get_provider_info("openai")

        assert info["name"] == "OpenAI-Compatible"
        assert "OPENAI_API_KEY" in info["required_config"]

    def test_get_provider_info_unknown(self):
        """Test getting info for unknown provider."""
        from ai.provider_factory import get_provider_info

        info = get_provider_info("unknown")

        assert "error" in info
