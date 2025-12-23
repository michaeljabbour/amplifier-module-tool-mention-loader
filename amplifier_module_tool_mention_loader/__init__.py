"""
amplifier-module-tool-mention-loader

Load file and folder context via @mention syntax for Amplifier CLI applications.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from amplifier_core import ToolResult

__version__ = "1.0.0"
__amplifier_module_type__ = "tool"


async def mount(coordinator, config: dict):
    """
    Mount function that registers the mention loader tool.

    Args:
        coordinator: Amplifier ModuleCoordinator instance
        config: Configuration dictionary with keys:
            - resolve_relative_to: str (default: "cwd")
            - try_extensions: list (default: [".md", ".txt", ".py"])
            - show_loaded_files: bool (default: True)
            - max_file_size: int (default: 1048576)
    """
    # Extract configuration
    resolve_relative_to = config.get("resolve_relative_to", "cwd")
    try_extensions = config.get("try_extensions", [".md", ".txt", ".py"])
    show_loaded_files = config.get("show_loaded_files", True)
    max_file_size = config.get("max_file_size", 1048576)

    # Create tool instance
    tool = MentionLoaderTool(
        resolve_relative_to=resolve_relative_to,
        try_extensions=try_extensions,
        show_loaded_files=show_loaded_files,
        max_file_size=max_file_size
    )

    # Register tool
    coordinator.mount_points["tools"][tool.name] = tool


class MentionLoaderTool:
    """Tool for loading file and folder context via @mention syntax."""

    def __init__(
        self,
        resolve_relative_to: str,
        try_extensions: List[str],
        show_loaded_files: bool,
        max_file_size: int
    ):
        """
        Initialize the mention loader tool.

        Args:
            resolve_relative_to: Where to resolve paths ("cwd" or "git_root")
            try_extensions: File extensions to try
            show_loaded_files: Whether to show loaded file paths
            max_file_size: Maximum file size in bytes
        """
        self.resolve_relative_to = resolve_relative_to
        self.try_extensions = try_extensions
        self.show_loaded_files = show_loaded_files
        self.max_file_size = max_file_size

    @property
    def name(self) -> str:
        """Tool name."""
        return "mention_loader"

    @property
    def description(self) -> str:
        """Tool description for Claude."""
        return "Load file or directory content when @mentions are used in prompts"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool input."""
        return {
            "type": "object",
            "properties": {
                "mentions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of @mentioned file or directory paths"
                }
            },
            "required": ["mentions"]
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """
        Load content for @mentioned files/directories.

        Args:
            input: Tool input dict containing 'mentions' key

        Returns:
            ToolResult with loaded content and metadata
        """
        # Extract mentions from input
        mentions = input.get("mentions", [])

        # Determine base path
        base_path = self._get_base_path()

        loaded_files = []
        content_parts = []

        for mention in mentions:
            # Remove @ prefix if present and strip whitespace
            path_str = mention.lstrip("@").strip()

            # Skip empty or whitespace-only mentions
            if not path_str:
                continue

            # Resolve the path
            resolved_path = self._resolve_path(base_path, path_str)

            if resolved_path and resolved_path.exists():
                if resolved_path.is_file():
                    # Load file content
                    file_content = self._load_file(resolved_path)
                    if file_content is not None:
                        loaded_files.append(str(resolved_path))
                        content_parts.append(f"# {resolved_path}\n\n{file_content}")
                elif resolved_path.is_dir():
                    # Load directory listing
                    dir_listing = self._load_directory(resolved_path)
                    loaded_files.append(str(resolved_path))
                    content_parts.append(f"# {resolved_path}/\n\n{dir_listing}")

        # Build result
        result = {
            "loaded_files": loaded_files,
            "content": "\n\n---\n\n".join(content_parts) if content_parts else None
        }

        if self.show_loaded_files and loaded_files:
            result["message"] = f"Loaded {len(loaded_files)} file(s): {', '.join(loaded_files)}"

        return ToolResult(success=True, output=result)

    def _get_base_path(self) -> Path:
        """
        Get the base path for resolving mentions.

        Returns:
            Base path (git root or CWD)
        """
        if self.resolve_relative_to == "git_root":
            git_root = self._get_git_root()
            if git_root:
                return git_root

        # Fallback to current working directory
        return Path.cwd()

    def _get_git_root(self) -> Optional[Path]:
        """
        Get the git repository root path.

        Returns:
            Path to git root, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                cwd=os.getcwd()
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _resolve_path(self, base_path: Path, path_str: str) -> Optional[Path]:
        """
        Resolve a path, trying extensions if needed.

        Args:
            base_path: Base directory for resolution
            path_str: Path string to resolve

        Returns:
            Resolved Path, or None if not found
        """
        # Try exact path first
        candidate = base_path / path_str
        if candidate.exists():
            return candidate

        # Try with extensions
        for ext in self.try_extensions:
            candidate_with_ext = base_path / f"{path_str}{ext}"
            if candidate_with_ext.exists():
                return candidate_with_ext

        return None

    def _load_file(self, file_path: Path) -> Optional[str]:
        """
        Load file content with size limit.

        Args:
            file_path: Path to file

        Returns:
            File content, or None if too large or unreadable
        """
        try:
            # Check file size
            if file_path.stat().st_size > self.max_file_size:
                return f"[File too large: {file_path.stat().st_size} bytes > {self.max_file_size} bytes]"

            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            return f"[Error reading file: {e}]"

    def _load_directory(self, dir_path: Path) -> str:
        """
        Load directory listing.

        Args:
            dir_path: Path to directory

        Returns:
            Directory listing as string
        """
        try:
            entries = []
            for item in sorted(dir_path.iterdir()):
                if item.is_file():
                    size = item.stat().st_size
                    entries.append(f"  - {item.name} ({size} bytes)")
                elif item.is_dir():
                    entries.append(f"  - {item.name}/")

            if entries:
                return "Directory contents:\n" + "\n".join(entries)
            else:
                return "Empty directory"
        except OSError as e:
            return f"[Error reading directory: {e}]"
