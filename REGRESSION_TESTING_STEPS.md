# Regression Testing: Complete Step-by-Step Guide

## Overview

This document provides step-by-step instructions for creating and using regression tests that help AI systems provide better testing insights and catch bugs early.

## Table of Contents

1. [What Are Regression Tests?](#what-are-regression-tests)
2. [Step-by-Step: Creating Regression Tests](#step-by-step-creating-regression-tests)
3. [Step-by-Step: Running and Analyzing](#step-by-step-running-and-analyzing)
4. [Step-by-Step: Fixing Issues Found](#step-by-step-fixing-issues-found)
5. [Real Example from This Project](#real-example-from-this-project)
6. [AI-Assisted Regression Testing](#ai-assisted-regression-testing)

---

## What Are Regression Tests?

**Regression tests** are tests that ensure:
- Existing functionality doesn't break when you make changes
- Edge cases are documented and protected
- Performance characteristics remain stable
- API contracts don't accidentally change

**Why they matter:**
- Catch bugs **before** users do
- Document expected behavior for future maintainers
- Give confidence when refactoring
- Serve as specification of "correctness"

---

## Step-by-Step: Creating Regression Tests

### Step 1: Identify Test Categories

Create test classes for each category:

```python
class TestEdgeCases:
    """Edge cases that could break with subtle changes"""

class TestBoundaryConditions:
    """Limits and boundaries (size, count, length)"""

class TestErrorRecovery:
    """Error handling and graceful degradation"""

class TestConfigurationRegressions:
    """Config changes that could break workflows"""

class TestBackwardCompatibility:
    """API contracts that must not change"""

class TestPerformanceRegressions:
    """Performance characteristics to maintain"""
```

### Step 2: Write Tests with Rich Documentation

**Template for each test:**

```python
@pytest.mark.asyncio
async def test_descriptive_name(self, config, fixtures):
    """
    REGRESSION: One-line summary of what's being tested.

    Why: Explain why this behavior matters
    What breaks: Describe the specific code change that would break this
    """
    # Arrange: Set up test conditions

    # Act: Execute the behavior being tested

    # Assert: Verify expected behavior
```

**Example:**

```python
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
```

### Step 3: Cover Edge Cases

**Essential edge cases to test:**

1. **Empty inputs**: `[]`, `""`, `None`
2. **Whitespace**: `"   "`, `"\t"`, `"\n"`
3. **Duplicates**: Same input multiple times
4. **Special characters**: Unicode, symbols, spaces in names
5. **Symlinks**: Followed or broken
6. **Very large/small**: At limits, one over/under
7. **Empty files**: 0 bytes but valid
8. **Binary files**: Non-text data
9. **Concurrent access**: Race conditions
10. **Missing resources**: Deleted between check and use

### Step 4: Add Performance Baselines

```python
@pytest.mark.asyncio
async def test_large_directory_performance(self, config, tmp_path):
    """Performance: Large directories should list quickly"""
    # Create 100 files
    large_dir = tmp_path / "large"
    large_dir.mkdir()
    for i in range(100):
        (large_dir / f"file{i}.txt").write_text(f"content{i}")

    tool = MentionLoaderTool(**config)

    import time
    start = time.time()
    result = await tool.execute(["@large/"])
    elapsed = time.time() - start

    # Should complete in under 1 second
    assert elapsed < 1.0
```

### Step 5: Test Backward Compatibility

```python
@pytest.mark.asyncio
async def test_tool_interface_stability(self, config):
    """
    REGRESSION: Tool interface must remain stable.

    Why: Coordinator depends on specific interface.
    What breaks: Renaming properties or changing signatures.
    """
    tool = MentionLoaderTool(**config)

    # These properties must exist and return correct types
    assert isinstance(tool.name, str)
    assert isinstance(tool.description, str)
    assert isinstance(tool.input_schema, dict)

    # Execute must be async
    assert asyncio.iscoroutinefunction(tool.execute)
```

---

## Step-by-Step: Running and Analyzing

### Step 1: Run Initial Baseline

```bash
# Run all regression tests
pytest tests/test_regression.py -v

# Save output to compare later
pytest tests/test_regression.py -v > baseline.txt
```

**What to look for:**
- How many tests pass vs. fail
- Any unexpected failures (regressions!)
- Performance test timings

### Step 2: Analyze Failures

For each failure, ask:

1. **Is this a regression?** (Broke existing functionality)
2. **Is this a new bug discovered?** (Never worked, now tested)
3. **Is this intentional?** (Expected behavior changed)

**Example output:**
```
FAILED test_whitespace_only_mention - AssertionError: assert ['/path'] == []
```

**Analysis:**
- **Expected**: Empty list (no files loaded)
- **Actual**: Current directory loaded
- **Conclusion**: Bug discovered! Whitespace should be handled

### Step 3: Categorize Issues

Create issues for each failure:

```markdown
## Issue #1: Whitespace-Only Mentions
**Severity**: Medium
**Category**: Edge Case
**Test**: test_whitespace_only_mention

**Problem**: Mentions containing only whitespace (@   ) resolve to current directory

**Root cause**: Code only strips @ but not whitespace:
`path_str = mention.lstrip("@")`  # "   " remains

**Fix**: Strip whitespace after removing @:
`path_str = mention.lstrip("@").strip()`
```

### Step 4: Compare Before/After

After making changes:

```bash
# Run tests again
pytest tests/test_regression.py -v > after.txt

# Compare
diff baseline.txt after.txt
```

**What to check:**
- **New failures** = Regression introduced
- **New passes** = Bug fixed
- **Same results** = No impact on these behaviors

---

## Step-by-Step: Fixing Issues Found

### Step 1: Reproduce Locally

Create a minimal reproduction:

```python
# Reproduce the issue outside tests
tool = MentionLoaderTool(config)
result = await tool.execute(["@   "])
print(result["loaded_files"])  # Shows current dir instead of []
```

### Step 2: Identify Root Cause

Trace through code:

```python
# In execute():
path_str = mention.lstrip("@")  # "   " after @ removed
# path_str = "   " (whitespace remains!)

resolved = base_path / path_str
# resolved = base_path / "   " = base_path (!)
```

**Root cause**: Whitespace not stripped, empty paths resolve to parent

### Step 3: Implement Fix

```python
# Before (buggy):
path_str = mention.lstrip("@")

# After (fixed):
path_str = mention.lstrip("@").strip()

# Add safety check:
if not path_str:
    continue  # Skip empty/whitespace mentions
```

### Step 4: Verify Fix

```bash
# Run specific test
pytest tests/test_regression.py::TestEdgeCases::test_whitespace_only_mention -v

# Should pass now
PASSED test_whitespace_only_mention
```

### Step 5: Run Full Suite

```bash
# Ensure fix didn't break anything else
pytest tests/ -v

# All tests should still pass
42 passed in 0.5s
```

### Step 6: Document the Fix

```python
# Add comment explaining the fix
# Remove @ prefix and strip whitespace
path_str = mention.lstrip("@").strip()

# Skip empty or whitespace-only mentions
# This prevents resolving whitespace to current directory
if not path_str:
    continue
```

---

## Real Example from This Project

### Our Results

**Created**: 23 regression tests
**Initial run**: 21 passed, 2 failed ✅
**Bugs found**: 2 real issues
**After fixes**: 23 passed, 0 failed ✅

### Issue #1: Whitespace-Only Mentions

**Test that found it:**
```python
async def test_whitespace_only_mention(self, test_config, temp_project):
    tool = MentionLoaderTool(**test_config)
    result = await tool.execute(["@   ", "@\t", "@"])
    assert result["loaded_files"] == []  # FAILED!
```

**Bug**: Returned current directory instead of empty list

**Root cause:**
```python
# Line 114 (buggy):
path_str = mention.lstrip("@")  # Leaves whitespace
```

**Fix:**
```python
# Lines 114-118 (fixed):
path_str = mention.lstrip("@").strip()
if not path_str:
    continue
```

**Impact**: Prevented accidental loading of wrong content from typos

---

### Issue #2: Empty Files Not Loading

**Test that found it:**
```python
async def test_empty_file(self, test_config, tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("")

    tool = MentionLoaderTool(**test_config)
    result = await tool.execute(["@empty.txt"])

    assert len(result["loaded_files"]) == 1  # FAILED!
```

**Bug**: Empty files (0 bytes) were skipped

**Root cause:**
```python
# Line 123 (buggy):
if file_content:  # Empty string "" is falsy!
    loaded_files.append(...)
```

**Fix:**
```python
# Line 127 (fixed):
if file_content is not None:  # Explicit None check
    loaded_files.append(...)
```

**Impact**: Ensured all valid files are acknowledged, even if empty

---

## AI-Assisted Regression Testing

### How AI Can Help

AI systems can analyze regression tests to:

1. **Identify patterns** in failures across test categories
2. **Suggest root causes** based on test names and assertions
3. **Generate additional tests** for uncovered edge cases
4. **Explain implications** of test failures
5. **Recommend fixes** based on similar patterns

### Prompting AI for Regression Insights

**Good prompts:**

```
"Analyze these regression test failures and identify common patterns:
[paste test output]

For each failure, explain:
1. What behavior is expected vs actual
2. Likely root cause in the code
3. Potential side effects if not fixed
4. Related edge cases that should also be tested"
```

```
"I'm refactoring [component]. Review these regression tests and tell me:
1. Which tests are most likely to fail
2. What new edge cases my changes might introduce
3. Performance implications to watch for"
```

```
"Create additional regression tests for [feature] covering:
1. Edge cases with empty/null/extreme values
2. Concurrent access scenarios
3. Backward compatibility concerns
4. Performance under load"
```

### AI Analysis of Our Tests

When AI analyzes our regression suite, it can provide:

**Pattern Recognition:**
```
"I notice 3 tests failed in TestEdgeCases:
- test_whitespace_only_mention
- test_empty_mention_list
- test_duplicate_mentions

Common pattern: All involve empty or unusual mention inputs.
Likely root cause: Input validation/sanitization logic.
Recommendation: Add robust input cleaning early in execute()."
```

**Impact Analysis:**
```
"The whitespace bug has HIGH impact because:
1. Common user mistake (accidental spaces)
2. Silent failure (loads wrong content without error)
3. Security concern (exposes unintended files)
4. Affects all use cases (not edge case)

Priority: Fix immediately before release."
```

**Test Coverage Suggestions:**
```
"Your regression suite covers these well:
✅ Edge cases (empty, whitespace, unicode)
✅ Boundary conditions (size limits)
✅ Error recovery (permissions, missing files)

Missing coverage:
❌ Network errors (if remote paths supported)
❌ Memory limits (very large files in memory)
❌ Circular symlinks (infinite loop potential)

Recommended: Add 3 tests for circular symlink handling."
```

---

## Best Practices Summary

### When Writing Regression Tests

1. ✅ **Document WHY**: Every test explains why it matters
2. ✅ **Document WHAT BREAKS**: Describe change that would break it
3. ✅ **Be Specific**: One concept per test
4. ✅ **Use Real Data**: Realistic filenames, sizes, patterns
5. ✅ **Test Edge Cases**: Empty, zero, max, null, whitespace
6. ✅ **Add Timing**: Performance baselines for critical paths
7. ✅ **Group Logically**: Organize by category for clarity

### When Tests Fail

1. ❌ **Don't immediately "fix" the test**
2. ✅ **Investigate thoroughly**: Regression or intentional?
3. ✅ **Document the bug**: What/why/impact
4. ✅ **Fix the code**: Not the test
5. ✅ **Verify comprehensively**: Run full suite
6. ✅ **Update docs**: Comment explaining the fix

### When Refactoring

1. ✅ **Run baseline first**: Know current state
2. ✅ **Make changes incrementally**: Small steps
3. ✅ **Run tests frequently**: After each change
4. ✅ **Compare results**: New failures = regressions
5. ✅ **Add new tests**: For new edge cases discovered
6. ✅ **Update tests**: If behavior intentionally changes

---

## Continuous Integration

Add to CI pipeline:

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run regression tests
        run: |
          pytest tests/test_regression.py -v --strict-markers
          pytest tests/test_regression.py --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Metrics to Track

Monitor over time:

| Metric | Goal | Current |
|--------|------|---------|
| Total regression tests | Increase with features | 23 |
| Passing percentage | 100% after fixes | 100% |
| New failures per commit | 0 (catch early) | 0 |
| Test execution time | < 1s (fast feedback) | 0.16s |
| Coverage | > 90% | 95% |

---

## Conclusion

Regression tests are **living documentation** that:
- Catch bugs before users do ✅
- Document edge cases for maintainers ✅
- Give confidence when refactoring ✅
- Serve as specification of "correct" ✅

**In our project:**
- Created 23 comprehensive regression tests
- Found and fixed 2 real bugs immediately
- All 42 tests now passing (19 original + 23 regression)
- Ready for CI integration

**Remember**: When in doubt, add a regression test!

---

## Quick Reference

```bash
# Run all regression tests
pytest tests/test_regression.py -v

# Run specific category
pytest tests/test_regression.py::TestEdgeCases -v

# Run with coverage
pytest tests/test_regression.py --cov=module --cov-report=html

# Run performance tests only
pytest tests/test_regression.py::TestPerformanceRegressions -v

# Compare before/after
pytest tests/test_regression.py -v > baseline.txt
# ... make changes ...
pytest tests/test_regression.py -v > after.txt
diff baseline.txt after.txt
```
