"""
Configuration validation tests for mention loader module.
"""

import pytest
from amplifier_module_tool_mention_loader import mount, MentionLoaderTool


class TestModuleMount:
    """Test module mounting and configuration."""

    @pytest.mark.asyncio
    async def test_mount_with_defaults(self, mock_coordinator):
        """Test mounting with default configuration."""
        config = {}
        await mount(mock_coordinator, config)

        # Verify tool was registered
        assert "mention_loader" in mock_coordinator.mount_points["tools"]

        tool = mock_coordinator.mount_points["tools"]["mention_loader"]
        assert isinstance(tool, MentionLoaderTool)
        assert tool.resolve_relative_to == "cwd"
        assert tool.try_extensions == [".md", ".txt", ".py"]
        assert tool.show_loaded_files is True
        assert tool.max_file_size == 1048576

    @pytest.mark.asyncio
    async def test_mount_with_custom_config(self, mock_coordinator):
        """Test mounting with custom configuration."""
        config = {
            "resolve_relative_to": "git_root",
            "try_extensions": [".md", ".rst"],
            "show_loaded_files": False,
            "max_file_size": 5242880
        }
        await mount(mock_coordinator, config)

        tool = mock_coordinator.mount_points["tools"]["mention_loader"]
        assert tool.resolve_relative_to == "git_root"
        assert tool.try_extensions == [".md", ".rst"]
        assert tool.show_loaded_files is False
        assert tool.max_file_size == 5242880


class TestToolProperties:
    """Test tool interface properties."""

    def test_tool_name(self, test_config):
        """Test that tool has correct name."""
        tool = MentionLoaderTool(**test_config)
        assert tool.name == "mention_loader"

    def test_tool_description(self, test_config):
        """Test that tool has description."""
        tool = MentionLoaderTool(**test_config)
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0

    def test_tool_input_schema(self, test_config):
        """Test that tool has valid JSON Schema."""
        tool = MentionLoaderTool(**test_config)
        schema = tool.input_schema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "mentions" in schema["properties"]
        assert schema["properties"]["mentions"]["type"] == "array"
        assert "required" in schema
        assert "mentions" in schema["required"]
