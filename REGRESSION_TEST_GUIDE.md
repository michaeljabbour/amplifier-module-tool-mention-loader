# Regression Testing Guide

## What Are Regression Tests?

Regression tests ensure that:
1. **Existing functionality doesn't break** when making changes
2. **Edge cases are documented** and protected
3. **Performance characteristics** remain stable
4. **API contracts** don't accidentally change

## Our Regression Test Results

### Tests Created: 23
### Tests Passing: 21 ✅
### Tests Failing: 2 ❌ (Found real issues!)

## Issues Found by Regression Tests

### Issue #1: Whitespace-Only Mentions
**Test**: `test_whitespace_only_mention`

**Problem**: When user types `@   ` (whitespace only), the code strips the `@` but then tries to resolve the whitespace as a path. This resolves to the current directory!

**What happens**:
```python
mention = "@   "
path_str = mention.lstrip("@")  # "   "
resolved = base_path / path_str  # base_path/"   " = base_path!
```

**Expected**: Gracefully skip whitespace-only mentions
**Actual**: Loads current directory

**Why it matters**: User typos shouldn't load unintended content

---

### Issue #2: Empty Files Not Loading
**Test**: `test_empty_file`

**Problem**: Empty files (0 bytes) return empty result instead of being included in loaded_files.

**What happens**: The file exists, opens successfully, but `read()` returns empty string `""`. This might be treated as falsy somewhere.

**Expected**: Empty file should appear in loaded_files
**Actual**: Empty file is skipped

**Why it matters**: Valid files (even if empty) should be acknowledged

---

## How to Use Regression Tests

### Step 1: Run Before Making Changes
```bash
pytest tests/test_regression.py -v
```

Establishes baseline - what works and what doesn't.

### Step 2: Make Your Code Changes
Refactor, optimize, add features...

### Step 3: Run After Making Changes
```bash
pytest tests/test_regression.py -v
```

### Step 4: Compare Results
- **New failures** = You broke something (regression!)
- **New passes** = You fixed an edge case (improvement!)
- **Same results** = Changes didn't affect these behaviors

### Step 5: Update Tests When Behavior Changes Intentionally
If you *intentionally* change behavior:
1. Update the test to reflect new expected behavior
2. Document WHY in the test docstring
3. Update the "Why it matters" section

## Regression Test Categories

### 1. Edge Cases (`TestEdgeCases`)
- Empty inputs
- Whitespace handling
- Duplicate mentions
- Special characters
- Unicode support
- Symlink following

**Purpose**: Catch subtle bugs that only appear with unusual inputs

### 2. Boundary Conditions (`TestBoundaryConditions`)
- Size limits (exactly at, one over)
- Empty files
- Very long filenames
- Deep directory nesting

**Purpose**: Catch off-by-one errors and limit violations

### 3. Error Recovery (`TestErrorRecovery`)
- Permission denied
- Binary files
- Concurrent execution
- Race conditions

**Purpose**: Ensure errors are handled gracefully without crashes

### 4. Configuration Regressions (`TestConfigurationRegressions`)
- Extension priority
- Boolean type enforcement
- Zero size limits

**Purpose**: Ensure configuration changes don't break user workflows

### 5. Backward Compatibility (`TestBackwardCompatibility`)
- Tool interface stability
- Return format stability
- Mount signature stability

**Purpose**: Protect API contracts from breaking changes

### 6. Performance Regressions (`TestPerformanceRegressions`)
- Large directory listing
- Many mentions at once

**Purpose**: Catch performance degradation early

## Best Practices

### When Writing Regression Tests

1. **Document WHY**: Every test should explain why it matters
2. **Document WHAT BREAKS**: Describe the specific change that would break this
3. **Be Specific**: Test one thing per test
4. **Use Realistic Data**: Real filenames, real paths, real sizes
5. **Test Edge Cases**: Empty, zero, max, null, whitespace
6. **Performance Baselines**: Add timing assertions for critical paths

### When Regression Tests Fail

1. **Don't immediately "fix" the test**: The test might be catching a real bug
2. **Investigate**: Is this intentional or a regression?
3. **If bug**: Fix the code, test passes
4. **If intentional**: Update test, document in commit message

### When Adding Features

1. **Add regression tests for the new feature**
2. **Test edge cases of the new feature**
3. **Test interaction with existing features**

## Running Different Test Suites

```bash
# All tests (validation + behavioral + regression)
pytest tests/ -v

# Only regression tests
pytest tests/test_regression.py -v

# Only edge cases
pytest tests/test_regression.py::TestEdgeCases -v

# Specific test
pytest tests/test_regression.py::TestEdgeCases::test_empty_mention_list -v

# With coverage
pytest tests/test_regression.py --cov=amplifier_module_tool_mention_loader

# Performance tests only
pytest tests/test_regression.py::TestPerformanceRegressions -v
```

## Next Steps

### Fix Issue #1: Whitespace-Only Mentions
**Location**: `amplifier_module_tool_mention_loader/__init__.py:execute()`

**Solution**: Strip whitespace after removing `@`, skip if empty:
```python
# Remove @ prefix if present
path_str = mention.lstrip("@").strip()

# Skip empty or whitespace-only mentions
if not path_str:
    continue
```

### Fix Issue #2: Empty Files Not Loading
**Location**: `amplifier_module_tool_mention_loader/__init__.py:_load_file()`

**Investigation needed**: Check if empty string is being filtered somewhere

**Potential fix**: Ensure empty content is still treated as valid:
```python
content = f.read()
return content  # Even if empty string ""
```

## Continuous Integration

Add to CI pipeline:
```yaml
- name: Run regression tests
  run: pytest tests/test_regression.py -v --strict-markers
```

This ensures regression tests run on every commit.

## Regression Test Metrics

Track over time:
- **Total regression tests**: Should increase as codebase grows
- **Passing percentage**: Should stay at 100% after initial fixes
- **New failures**: Each one is a potential regression to investigate
- **Performance baselines**: Should not degrade without explicit reason

## Conclusion

Regression tests are **living documentation** of your codebase's expected behavior. They:
- Catch bugs before users do
- Document edge cases for future maintainers
- Give confidence when refactoring
- Serve as specification for what "correct" means

**When in doubt, add a regression test!**
