"""
Behavioral tests for mention loader functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from amplifier_module_tool_mention_loader import MentionLoaderTool


class TestFileLoading:
    """Test file loading functionality."""

    @pytest.mark.asyncio
    async def test_load_single_file(self, test_config, temp_project):
        """Test loading a single file."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert result["loaded_files"] == [str(temp_project / "README.md")]
        assert "# Test Project" in result["content"]
        assert "This is a test." in result["content"]

    @pytest.mark.asyncio
    async def test_load_multiple_files(self, test_config, temp_project):
        """Test loading multiple files."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md", "@config.txt"])

        assert len(result["loaded_files"]) == 2
        assert str(temp_project / "README.md") in result["loaded_files"]
        assert str(temp_project / "config.txt") in result["loaded_files"]
        assert "# Test Project" in result["content"]
        assert "setting=value" in result["content"]

    @pytest.mark.asyncio
    async def test_load_with_extension_resolution(self, test_config, temp_project):
        """Test that extensions are tried automatically."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            # Request "README" without extension
            result = await tool.execute(["@README"])

        # Should find README.md
        assert str(temp_project / "README.md") in result["loaded_files"]
        assert "# Test Project" in result["content"]

    @pytest.mark.asyncio
    async def test_load_missing_file(self, test_config, temp_project):
        """Test that missing files are handled gracefully."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@nonexistent.md"])

        # Should return empty result
        assert result["loaded_files"] == []
        assert result["content"] is None

    @pytest.mark.asyncio
    async def test_load_file_size_limit(self, test_config, temp_project):
        """Test that large files are rejected."""
        # Create a config with small file size limit
        small_config = test_config.copy()
        small_config["max_file_size"] = 10  # 10 bytes

        tool = MentionLoaderTool(**small_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        # File should be loaded but with size warning
        assert len(result["loaded_files"]) == 1
        assert "[File too large:" in result["content"]


class TestDirectoryLoading:
    """Test directory loading functionality."""

    @pytest.mark.asyncio
    async def test_load_directory(self, test_config, temp_project):
        """Test loading a directory listing."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@docs/"])

        assert str(temp_project / "docs") in result["loaded_files"]
        assert "Directory contents:" in result["content"]
        assert "guide.md" in result["content"]

    @pytest.mark.asyncio
    async def test_load_directory_without_slash(self, test_config, temp_project):
        """Test that directories work without trailing slash."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@docs"])

        assert str(temp_project / "docs") in result["loaded_files"]
        assert "Directory contents:" in result["content"]


class TestPathResolution:
    """Test path resolution logic."""

    @pytest.mark.asyncio
    async def test_resolve_from_cwd(self, test_config, temp_project):
        """Test resolving paths from CWD."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert result["loaded_files"] == [str(temp_project / "README.md")]

    @pytest.mark.asyncio
    async def test_resolve_from_git_root(self, test_config, temp_project):
        """Test resolving paths from git root."""
        git_config = test_config.copy()
        git_config["resolve_relative_to"] = "git_root"

        tool = MentionLoaderTool(**git_config)

        with patch.object(tool, '_get_git_root', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert result["loaded_files"] == [str(temp_project / "README.md")]

    @pytest.mark.asyncio
    async def test_git_root_fallback_to_cwd(self, test_config, temp_project):
        """Test that git_root falls back to CWD when not in git repo."""
        git_config = test_config.copy()
        git_config["resolve_relative_to"] = "git_root"

        tool = MentionLoaderTool(**git_config)

        with patch.object(tool, '_get_git_root', return_value=None), \
             patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert result["loaded_files"] == [str(temp_project / "README.md")]


class TestShowLoadedFiles:
    """Test show_loaded_files configuration."""

    @pytest.mark.asyncio
    async def test_show_loaded_files_true(self, test_config, temp_project):
        """Test that loaded files message is shown when enabled."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert "message" in result
        assert "Loaded 1 file(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_show_loaded_files_false(self, test_config, temp_project):
        """Test that loaded files message is hidden when disabled."""
        silent_config = test_config.copy()
        silent_config["show_loaded_files"] = False

        tool = MentionLoaderTool(**silent_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert "message" not in result


class TestMentionParsing:
    """Test @mention syntax parsing."""

    @pytest.mark.asyncio
    async def test_parse_with_at_symbol(self, test_config, temp_project):
        """Test that @symbol is stripped from mentions."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        assert len(result["loaded_files"]) == 1

    @pytest.mark.asyncio
    async def test_parse_without_at_symbol(self, test_config, temp_project):
        """Test that mentions work without @ symbol."""
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["README.md"])

        assert len(result["loaded_files"]) == 1
