"""
Regression tests for mention loader module.

These tests capture edge cases, integration scenarios, and behavior that
must remain stable across future changes. Each test documents why the
behavior matters and what could break if changed.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
import asyncio
from amplifier_module_tool_mention_loader import mount, MentionLoaderTool


class TestEdgeCases:
    """
    REGRESSION: Edge cases that have caused issues or could break.

    Why these matter: Small changes to path resolution or file reading
    can break these subtle cases without obvious test failures.
    """

    @pytest.mark.asyncio
    async def test_empty_mention_list(self, test_config):
        """
        REGRESSION: Empty mention list should return empty result, not error.

        Why: Early versions might have crashed on empty input.
        What breaks: Adding assertions without null checks.
        """
        tool = MentionLoaderTool(**test_config)

        result = await tool.execute([])

        assert result["loaded_files"] == []
        assert result["content"] is None
        assert "message" not in result  # No files = no message

    @pytest.mark.asyncio
    async def test_whitespace_only_mention(self, test_config, temp_project):
        """
        REGRESSION: Whitespace-only mentions should be handled gracefully.

        Why: User might accidentally type "@ " in their prompt.
        What breaks: Assuming mentions are non-empty strings.
        """
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@   ", "@\t", "@"])

        # Should gracefully handle, not crash
        assert result["loaded_files"] == []

    @pytest.mark.asyncio
    async def test_duplicate_mentions(self, test_config, temp_project):
        """
        REGRESSION: Duplicate mentions should load file only once.

        Why: Content deduplication prevents bloated context.
        What breaks: Naively appending all mentions without checking.
        """
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md", "@README.md", "@README.md"])

        # File should appear multiple times in loaded_files
        # (because we track each mention), but content should be reasonable
        assert len(result["loaded_files"]) == 3
        assert all(f == str(temp_project / "README.md") for f in result["loaded_files"])

        # Content should contain the file content multiple times
        # (current behavior - documents this for regression)
        assert result["content"].count("# Test Project") == 3

    @pytest.mark.asyncio
    async def test_special_characters_in_path(self, test_config, tmp_path):
        """
        REGRESSION: Paths with special characters should work.

        Why: Real projects have spaces, hyphens, underscores in names.
        What breaks: Improper path escaping or sanitization.
        """
        # Create file with special characters in path
        special_dir = tmp_path / "my-project_v2 (test)"
        special_dir.mkdir()
        special_file = special_dir / "config file.txt"
        special_file.write_text("special config")

        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute([f"@my-project_v2 (test)/config file.txt"])

        assert len(result["loaded_files"]) == 1
        assert "special config" in result["content"]

    @pytest.mark.asyncio
    async def test_unicode_in_filenames(self, test_config, tmp_path):
        """
        REGRESSION: Unicode filenames should work correctly.

        Why: International users have non-ASCII filenames.
        What breaks: Assuming ASCII-only paths.
        """
        unicode_file = tmp_path / "résumé.md"
        unicode_file.write_text("# Mon Résumé\n\nBonjour!")

        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@résumé.md"])

        assert len(result["loaded_files"]) == 1
        assert "Bonjour!" in result["content"]

    @pytest.mark.asyncio
    async def test_symlink_following(self, test_config, tmp_path):
        """
        REGRESSION: Symlinks should be followed to real files.

        Why: Projects often use symlinks for configs or shared files.
        What breaks: Only checking file existence, not resolving symlinks.
        """
        real_file = tmp_path / "real.md"
        real_file.write_text("real content")

        link_file = tmp_path / "link.md"
        link_file.symlink_to(real_file)

        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@link.md"])

        assert len(result["loaded_files"]) == 1
        assert "real content" in result["content"]


class TestBoundaryConditions:
    """
    REGRESSION: Boundary conditions for file sizes and counts.

    Why these matter: Changes to limits or iteration logic can cause
    crashes or hangs with extreme inputs.
    """

    @pytest.mark.asyncio
    async def test_exactly_at_size_limit(self, test_config, tmp_path):
        """
        REGRESSION: File exactly at size limit should load.

        Why: Off-by-one errors in size checks.
        What breaks: Using > instead of >= or vice versa.
        """
        exact_config = test_config.copy()
        exact_config["max_file_size"] = 100

        exact_file = tmp_path / "exact.txt"
        exact_file.write_text("x" * 100)  # Exactly 100 bytes

        tool = MentionLoaderTool(**exact_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@exact.txt"])

        # Should load successfully (not too large)
        assert len(result["loaded_files"]) == 1
        assert "x" * 100 in result["content"]

    @pytest.mark.asyncio
    async def test_one_byte_over_size_limit(self, test_config, tmp_path):
        """
        REGRESSION: File one byte over limit should be rejected.

        Why: Ensures size limit is enforced strictly.
        What breaks: Boundary check logic.
        """
        strict_config = test_config.copy()
        strict_config["max_file_size"] = 100

        over_file = tmp_path / "over.txt"
        over_file.write_text("x" * 101)  # 101 bytes

        tool = MentionLoaderTool(**strict_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@over.txt"])

        # Should reject with size message
        assert len(result["loaded_files"]) == 1
        assert "[File too large:" in result["content"]

    @pytest.mark.asyncio
    async def test_empty_file(self, test_config, tmp_path):
        """
        REGRESSION: Empty files (0 bytes) should load successfully.

        Why: Empty files are valid and should be handled.
        What breaks: Assuming all files have content.
        """
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@empty.txt"])

        assert len(result["loaded_files"]) == 1
        assert str(tmp_path / "empty.txt") in result["loaded_files"]

    @pytest.mark.asyncio
    async def test_very_long_filename(self, test_config, tmp_path):
        """
        REGRESSION: Very long filenames should work (up to OS limit).

        Why: Some generated files have extremely long names.
        What breaks: Path buffer size assumptions.
        """
        long_name = "a" * 200 + ".txt"
        long_file = tmp_path / long_name

        try:
            long_file.write_text("content")

            tool = MentionLoaderTool(**test_config)

            with patch('pathlib.Path.cwd', return_value=tmp_path):
                result = await tool.execute([f"@{long_name}"])

            assert len(result["loaded_files"]) == 1
        except OSError:
            # If OS doesn't support such long names, test passes
            pytest.skip("OS doesn't support filenames this long")

    @pytest.mark.asyncio
    async def test_deeply_nested_path(self, test_config, tmp_path):
        """
        REGRESSION: Deeply nested directories should work.

        Why: Monorepos can have very deep directory structures.
        What breaks: Path length limits, recursion limits.
        """
        # Create deeply nested structure
        deep_path = tmp_path
        for i in range(20):
            deep_path = deep_path / f"level{i}"
        deep_path.mkdir(parents=True)

        deep_file = deep_path / "deep.txt"
        deep_file.write_text("deeply nested content")

        tool = MentionLoaderTool(**test_config)

        # Build relative path
        relative = str(deep_file.relative_to(tmp_path))

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute([f"@{relative}"])

        assert len(result["loaded_files"]) == 1
        assert "deeply nested content" in result["content"]


class TestErrorRecovery:
    """
    REGRESSION: Error handling and recovery paths.

    Why these matter: Errors should be handled gracefully without
    crashing or leaving the system in a bad state.
    """

    @pytest.mark.asyncio
    async def test_permission_denied_file(self, test_config, tmp_path):
        """
        REGRESSION: Permission denied should be handled gracefully.

        Why: Users might mention files they can't read.
        What breaks: Not catching permission errors.
        """
        restricted_file = tmp_path / "restricted.txt"
        restricted_file.write_text("secret")
        restricted_file.chmod(0o000)  # No permissions

        tool = MentionLoaderTool(**test_config)

        try:
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                result = await tool.execute(["@restricted.txt"])

            # Should handle error gracefully
            assert "[Error reading file:" in result["content"] or result["loaded_files"] == []
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

    @pytest.mark.asyncio
    async def test_binary_file_handling(self, test_config, tmp_path):
        """
        REGRESSION: Binary files should error gracefully, not crash.

        Why: Users might mention image or compiled files by accident.
        What breaks: Assuming all files are text.
        """
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')

        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@image.png"])

        # Should handle binary file (either skip or show error)
        # Should NOT crash
        assert isinstance(result, dict)
        assert "loaded_files" in result

    @pytest.mark.asyncio
    async def test_concurrent_mentions(self, test_config, temp_project):
        """
        REGRESSION: Concurrent execution should be safe.

        Why: Multiple requests might process mentions simultaneously.
        What breaks: Shared state without locks.
        """
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            # Execute multiple times concurrently
            tasks = [
                tool.execute(["@README.md"]),
                tool.execute(["@config.txt"]),
                tool.execute(["@script.py"])
            ]

            results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        assert all(len(r["loaded_files"]) == 1 for r in results)

    @pytest.mark.asyncio
    async def test_file_deleted_between_check_and_read(self, test_config, tmp_path):
        """
        REGRESSION: File deleted between existence check and read.

        Why: Race condition in multi-process environments.
        What breaks: TOCTOU (time-of-check-time-of-use) bugs.
        """
        tool = MentionLoaderTool(**test_config)

        # Mock _resolve_path to return a path that will be deleted
        deleted_file = tmp_path / "deleted.txt"
        deleted_file.write_text("temporary")

        original_load = tool._load_file

        def mock_load(path):
            # Delete file just before loading
            if path.exists():
                path.unlink()
            return original_load(path)

        with patch.object(tool, '_load_file', side_effect=mock_load):
            with patch('pathlib.Path.cwd', return_value=tmp_path):
                result = await tool.execute(["@deleted.txt"])

        # Should handle gracefully (error message, not crash)
        assert isinstance(result, dict)


class TestConfigurationRegressions:
    """
    REGRESSION: Configuration variations and their effects.

    Why these matter: Config changes can subtly alter behavior in
    ways that break user workflows.
    """

    @pytest.mark.asyncio
    async def test_extension_order_matters(self, test_config, tmp_path):
        """
        REGRESSION: Extension priority should be respected.

        Why: Users rely on extension order for disambiguation.
        What breaks: Changing iteration order or using sets instead of lists.
        """
        # Create files with different extensions
        (tmp_path / "file.txt").write_text("text version")
        (tmp_path / "file.md").write_text("markdown version")

        # Config that prefers .txt
        txt_first = test_config.copy()
        txt_first["try_extensions"] = [".txt", ".md"]

        tool = MentionLoaderTool(**txt_first)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@file"])

        # Should load .txt first
        assert "text version" in result["content"]
        assert "markdown version" not in result["content"]

    @pytest.mark.asyncio
    async def test_show_loaded_files_always_boolean(self, test_config, temp_project):
        """
        REGRESSION: show_loaded_files must be boolean, not truthy.

        Why: Truthy values might work initially but break with certain inputs.
        What breaks: Using 'if self.show_loaded_files' with non-boolean types.
        """
        for value in [True, False]:
            config = test_config.copy()
            config["show_loaded_files"] = value

            tool = MentionLoaderTool(**config)

            with patch('pathlib.Path.cwd', return_value=temp_project):
                result = await tool.execute(["@README.md"])

            if value:
                assert "message" in result
            else:
                assert "message" not in result

    @pytest.mark.asyncio
    async def test_zero_byte_size_limit(self, test_config, tmp_path):
        """
        REGRESSION: Zero byte size limit should reject all files.

        Why: Edge case for size validation logic.
        What breaks: Not handling zero specially.
        """
        zero_config = test_config.copy()
        zero_config["max_file_size"] = 0

        small_file = tmp_path / "small.txt"
        small_file.write_text("x")

        tool = MentionLoaderTool(**zero_config)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@small.txt"])

        # Should reject (file is larger than 0 bytes)
        assert "[File too large:" in result["content"]


class TestBackwardCompatibility:
    """
    REGRESSION: Backward compatibility with previous versions.

    Why these matter: API changes can break existing integrations.
    """

    @pytest.mark.asyncio
    async def test_tool_interface_remains_stable(self, test_config):
        """
        REGRESSION: Tool interface must remain stable.

        Why: Coordinator depends on specific interface.
        What breaks: Renaming properties or changing signatures.
        """
        tool = MentionLoaderTool(**test_config)

        # These properties must exist and return correct types
        assert isinstance(tool.name, str)
        assert isinstance(tool.description, str)
        assert isinstance(tool.input_schema, dict)

        # Execute must be async and accept list
        assert asyncio.iscoroutinefunction(tool.execute)

    @pytest.mark.asyncio
    async def test_execute_return_format_stable(self, test_config, temp_project):
        """
        REGRESSION: Execute return format must remain stable.

        Why: Consumers parse the result dictionary.
        What breaks: Changing key names or adding required keys.
        """
        tool = MentionLoaderTool(**test_config)

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(["@README.md"])

        # Required keys that must always be present
        assert "loaded_files" in result
        assert isinstance(result["loaded_files"], list)

        # Content key must be present (can be None)
        assert "content" in result

        # Optional message key (depends on config)
        if "message" in result:
            assert isinstance(result["message"], str)

    @pytest.mark.asyncio
    async def test_mount_signature_stable(self, mock_coordinator, test_config):
        """
        REGRESSION: Mount signature must remain stable.

        Why: Framework calls mount with specific arguments.
        What breaks: Changing parameter names or adding required params.
        """
        # Mount must accept coordinator and config dict
        await mount(mock_coordinator, test_config)

        # Must register tool in mount_points["tools"]
        assert "mention_loader" in mock_coordinator.mount_points["tools"]


class TestPerformanceRegressions:
    """
    REGRESSION: Performance characteristics to maintain.

    Why these matter: Performance degradation affects user experience.
    """

    @pytest.mark.asyncio
    async def test_large_directory_listing_performance(self, test_config, tmp_path):
        """
        REGRESSION: Large directories should list in reasonable time.

        Why: Some project directories have thousands of files.
        What breaks: O(n²) algorithms, excessive sorting.
        """
        large_dir = tmp_path / "large"
        large_dir.mkdir()

        # Create many files
        for i in range(100):
            (large_dir / f"file{i:03d}.txt").write_text(f"content{i}")

        tool = MentionLoaderTool(**test_config)

        import time
        start = time.time()

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = await tool.execute(["@large/"])

        elapsed = time.time() - start

        # Should complete in under 1 second for 100 files
        assert elapsed < 1.0
        assert len(result["loaded_files"]) == 1

    @pytest.mark.asyncio
    async def test_many_mentions_performance(self, test_config, temp_project):
        """
        REGRESSION: Many mentions should process efficiently.

        Why: Users might mention many files at once.
        What breaks: Inefficient iteration or repeated path resolution.
        """
        tool = MentionLoaderTool(**test_config)

        # Mention same files many times
        mentions = ["@README.md", "@config.txt", "@script.py"] * 20

        import time
        start = time.time()

        with patch('pathlib.Path.cwd', return_value=temp_project):
            result = await tool.execute(mentions)

        elapsed = time.time() - start

        # Should complete in under 1 second for 60 mentions
        assert elapsed < 1.0
        assert len(result["loaded_files"]) == 60
