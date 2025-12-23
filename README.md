# amplifier-module-tool-mention-loader

Load file and folder context via @mention syntax for Amplifier CLI applications.

## Overview

This module enables Claude to automatically load file and directory context when you use @mention syntax in your prompts. Simply type `@filename.md` or `@directory/` and the content will be loaded before your prompt is sent to the AI.

## Features

- **@File Mentions**: Load individual files with `@README.md`
- **@Directory Mentions**: Load directory listings with `@docs/`
- **Extension Resolution**: Automatically tries common extensions (.md, .txt, .py)
- **Git-Aware**: Resolves paths relative to git root or CWD
- **Graceful Handling**: Silently skips missing files (no errors)
- **Deduplication**: Handles multiple mentions of the same file efficiently

## How It Works

1. **Type @mentions**: Include @mentions in your prompt: `@README.md explain this project`
2. **Auto-Resolution**: Module resolves paths and loads content
3. **Context Injection**: Content prepends to your message before sending to Claude
4. **AI Understanding**: Claude sees the full context and responds accordingly

## Installation

Add to your bundle's tools section:

```yaml
tools:
  - module: tool-mention-loader
    source: git+https://github.com/michaeljabbour/amplifier-module-tool-mention-loader@main
    config:
      resolve_relative_to: cwd
      try_extensions: [".md", ".txt", ".py"]
      show_loaded_files: true
      max_file_size: 1048576
```

Or install locally for development:

```yaml
tools:
  - module: tool-mention-loader
    source: git+file:///path/to/amplifier-module-tool-mention-loader
    config:
      resolve_relative_to: cwd
      try_extensions: [".md", ".txt", ".py"]
```

## Configuration

### `resolve_relative_to` (string, default: "cwd")

Where to resolve relative paths.

```yaml
resolve_relative_to: cwd      # Current working directory
resolve_relative_to: git_root # Git repository root (falls back to cwd)
```

### `try_extensions` (list, default: [".md", ".txt", ".py"])

File extensions to try when exact file not found.

```yaml
try_extensions: [".md", ".txt", ".py"]  # Default
try_extensions: [".md", ".rst"]         # Documentation only
```

### `show_loaded_files` (boolean, default: true)

Display which files were loaded.

```yaml
show_loaded_files: true   # Show loaded file paths
show_loaded_files: false  # Silent loading
```

### `max_file_size` (integer, default: 1048576)

Maximum file size in bytes (default: 1MB).

```yaml
max_file_size: 1048576  # 1MB (default)
max_file_size: 5242880  # 5MB
```

## Usage Examples

### Example 1: Single File

```
@README.md explain the project architecture
```

Claude sees README.md content and explains the architecture.

### Example 2: Multiple Files

```
@src/auth.py @tests/test_auth.py review these files for security issues
```

Claude sees both files and performs security review.

### Example 3: Directory Listing

```
@docs/ what documentation is available?
```

Claude sees directory structure and lists available docs.

### Example 4: Extension Resolution

```
@README explain this
```

Module tries `README`, then `README.md`, `README.txt`, `README.py` until found.

## Architecture

This module follows official Amplifier module conventions:

- **Entry Point**: `async def mount(coordinator, config)`
- **Tool Registration**: Registers tool via `coordinator.mount_points["tools"]`
- **Hook Integration**: Optional `prompt:submit` hook for auto-loading
- **Module Type**: Tool module (`__amplifier_module_type__ = "tool"`)
- **Dependencies**: Zero dependencies (self-contained)
- **Testing**: pytest with `asyncio_mode = "strict"`

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/michaeljabbour/amplifier-module-tool-mention-loader.git
cd amplifier-module-tool-mention-loader

# Install dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=amplifier_module_tool_mention_loader
```

### Project Structure

```
amplifier-module-tool-mention-loader/
├── amplifier_module_tool_mention_loader/
│   └── __init__.py                    # Module implementation
├── tests/
│   ├── conftest.py                    # Test fixtures
│   ├── test_validation.py             # Config validation tests
│   └── test_behavioral.py             # Behavioral tests
├── pyproject.toml                     # Package metadata
├── LICENSE                            # MIT License
├── README.md                          # This file
├── CODE_OF_CONDUCT.md                 # Community guidelines
├── SECURITY.md                        # Security policy
└── SUPPORT.md                         # Support resources
```

## Contributing

Contributions are welcome! Please:

1. Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
2. Check [existing issues](../../issues)
3. Create an issue before major changes
4. Follow existing code style
5. Add tests for new features
6. Update documentation

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

See [SUPPORT.md](SUPPORT.md) for help and community resources.

## Acknowledgments

Built for the [Amplifier](https://github.com/microsoft/amplifier) ecosystem.
