"""
Pytest configuration and fixtures for mention loader tests.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator for testing."""
    coordinator = Mock()
    coordinator.mount_points = {"tools": {}}
    coordinator.hooks = Mock()
    return coordinator


@pytest.fixture
def test_config():
    """Default test configuration."""
    return {
        "resolve_relative_to": "cwd",
        "try_extensions": [".md", ".txt", ".py"],
        "show_loaded_files": True,
        "max_file_size": 1048576
    }


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing."""
    # Create project directory
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create test files
    (project_dir / "README.md").write_text("# Test Project\n\nThis is a test.")
    (project_dir / "config.txt").write_text("setting=value\n")
    (project_dir / "script.py").write_text("print('hello')\n")

    # Create subdirectory
    docs_dir = project_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide\n\nInstructions here.")

    return project_dir
