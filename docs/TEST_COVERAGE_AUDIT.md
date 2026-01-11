# Test Coverage Audit

**Audit Date:** 2026-01-10
**Total Test Files:** 44
**Total Test Functions:** 726

## Executive Summary

The Null Terminal test suite has **good foundational coverage** but has **critical gaps** in key areas. The codebase follows testing best practices with proper fixtures and async patterns.

### Strengths
- Comprehensive unit tests for config, AI factory, and storage
- Good integration test coverage for UI interactions
- Proper use of `mock_home` fixture to protect user data
- Async testing patterns with `pytest-asyncio`

### Critical Gaps
- **No tests for `ai/` provider implementations** (only factory tested)
- **Minimal `handlers/ai_executor.py` testing** (complexity hotspot)
- **No tests for most widgets** (blocks, sidebar, status_bar)
- **No tests for screens** (provider, config, prompts screens)

---

## Coverage by Module

### Well-Covered (>70%)

| Module | Test File | Functions | Coverage |
|--------|-----------|-----------|----------|
| `config/storage.py` | `test_storage.py` | 46 | Excellent |
| `config/settings.py` | `test_settings.py` | 32 | Excellent |
| `config/defaults.py` | `test_defaults.py` | 27 | Excellent |
| `config/keys.py` | `test_keys.py` | 17 | Good |
| `ai/factory.py` | `test_factory.py` | 47 | Excellent |
| `ai/thinking.py` | `test_thinking.py` | 56 | Excellent |
| `ai/base.py` | `test_base.py` | 36 | Good |
| `prompts/manager.py` | `test_manager.py` | 31 | Good |
| `prompts/templates.py` | `test_templates.py` | 22 | Good |
| `tools/builtin.py` | `test_builtin.py` | 38 | Good |
| `tools/registry.py` | `test_registry.py` | 26 | Good |
| `themes.py` | `test_themes.py` (unit) | 36 | Good |

### Moderately Covered (30-70%)

| Module | Test File | Functions | Notes |
|--------|-----------|-----------|-------|
| `ai/manager.py` | `test_manager.py` | 22 | Missing streaming tests |
| `mcp/manager.py` | `test_manager.py` | 7 | Basic coverage only |
| `mcp/client.py` | `test_client.py` | 6 | Missing error cases |
| `mcp/catalog.py` | `test_mcp_catalog.py` | 23 | Good catalog tests |
| `handlers/input.py` | `test_input.py` | 6 | Missing edge cases |
| `managers/process.py` | `test_process.py` | 11 | Basic coverage |

### Poorly Covered (<30%)

| Module | Test File | Functions | Gap |
|--------|-----------|-----------|-----|
| `handlers/ai_executor.py` | `test_ai_executor.py` | 3 | **CRITICAL** - Complexity hotspot |
| `handlers/cli_executor.py` | `test_cli_executor.py` | 2 | Minimal |
| `handlers/execution.py` | `test_execution.py` | 2 | Facade only |
| `commands/todo.py` | `test_todo.py` | 5 | Missing command tests |

### No Test Coverage

| Module | Priority | Reason |
|--------|----------|--------|
| `ai/ollama.py` | HIGH | Primary local provider |
| `ai/openai_compat.py` | HIGH | Base for 10+ providers |
| `ai/anthropic.py` | MEDIUM | Major cloud provider |
| `ai/google_*.py` | MEDIUM | Growing usage |
| `widgets/blocks/*.py` | HIGH | Core UI components |
| `widgets/sidebar.py` | MEDIUM | Navigation component |
| `widgets/status_bar.py` | MEDIUM | State display |
| `widgets/palette.py` | LOW | Command palette |
| `screens/provider.py` | MEDIUM | Provider config UI |
| `screens/config.py` | MEDIUM | Settings UI |
| `screens/prompts.py` | LOW | Prompt management |
| `context.py` | HIGH | Context window logic |
| `ai/rag.py` | MEDIUM | Only 3 basic tests |
| `managers/agent.py` | MEDIUM | Agent session logic |
| `managers/branch.py` | LOW | Branching logic |
| `commands/ai.py` | MEDIUM | AI commands |
| `commands/core.py` | MEDIUM | Core commands |
| `commands/mcp.py` | MEDIUM | MCP commands |

---

## Integration Test Coverage

### Good Coverage
- App mounting and structure (`test_app.py`)
- Block creation and rendering (`test_blocks.py`)
- Input handling and modes (`test_input.py`)
- Keybindings (`test_keybindings.py`)
- Screen opening/closing (`test_screens.py`)
- Theme switching (`test_themes.py`)

### Missing Integration Tests
- AI response streaming and rendering
- Agent mode multi-step execution
- MCP tool discovery and execution
- Session save/load/export
- Provider switching
- Context window management
- File tree sidebar interaction

---

## Critical Test Gaps

### 1. AI Executor (handlers/ai_executor.py)

**Current:** 3 tests
**Needed:** 20+ tests

```python
# Missing test scenarios:
- test_streaming_text_response
- test_streaming_with_thinking_extraction
- test_tool_call_approval_flow
- test_tool_call_rejection_flow
- test_agent_mode_iteration
- test_agent_mode_max_iterations
- test_agent_mode_cancellation
- test_context_building
- test_error_handling_during_stream
- test_token_usage_tracking
- test_cost_calculation
```

### 2. Provider Implementations (ai/*.py)

**Current:** 0 tests per provider
**Needed:** Per-provider test files

```python
# Each provider should test:
- test_validate_connection_success
- test_validate_connection_failure
- test_list_models
- test_generate_streaming
- test_generate_with_tools
- test_error_handling
- test_api_key_validation
```

### 3. Block Widgets (widgets/blocks/*.py)

**Current:** Integration only
**Needed:** Unit tests for widget logic

```python
# Missing widget tests:
- test_ai_response_block_rendering
- test_thinking_widget_toggle
- test_tool_accordion_expand_collapse
- test_iteration_widget_nested_tools
- test_command_block_exit_code_display
```

### 4. Context Manager (context.py)

**Current:** 0 tests
**Needed:** Core functionality tests

```python
# Missing context tests:
- test_build_messages_from_blocks
- test_context_truncation
- test_token_estimation
- test_message_ordering
```

---

## Recommendations

### Immediate Priority (Week 1)

1. **Add context.py tests** - Core functionality with no coverage
2. **Expand ai_executor tests** - Most complex code path
3. **Add provider mock tests** - Test with mocked HTTP responses

### Short Term (Month 1)

4. **Widget unit tests** - Test block widget logic
5. **Screen tests** - Test modal screen interactions
6. **Command tests** - Test slash command handlers

### Long Term

7. **End-to-end tests** - Full user flow testing
8. **Performance tests** - Streaming latency, UI responsiveness
9. **Snapshot tests** - UI regression detection

---

## Test Infrastructure Notes

### Existing Fixtures

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `mock_home` | function | Temp home directory |
| `mock_storage` | function | Temp database |
| `temp_workdir` | function | Temp working directory |
| `running_app` | function | App with pilot |
| `mock_ai_components` | function (auto) | Mock AI/MCP |

### Missing Fixtures Needed

```python
# Proposed new fixtures:

@pytest.fixture
def mock_provider():
    """Create a mock LLMProvider with streaming support."""
    pass

@pytest.fixture
def mock_streaming_response():
    """Generate mock StreamChunk sequence."""
    pass

@pytest.fixture
async def app_with_ai_response(running_app):
    """App with a completed AI response block."""
    pass
```

### Test Organization

Current structure is good. Suggested additions:

```
tests/
├── unit/
│   ├── widgets/          # NEW: Widget unit tests
│   │   ├── test_blocks.py
│   │   ├── test_sidebar.py
│   │   └── test_status_bar.py
│   └── ai/
│       ├── test_ollama.py    # NEW: Provider tests
│       └── test_anthropic.py
├── integration/
│   ├── test_ai_flow.py       # NEW: AI interaction tests
│   └── test_agent_flow.py    # NEW: Agent mode tests
└── e2e/                      # NEW: End-to-end tests
    └── test_user_flows.py
```

---

## Coverage Goals

| Milestone | Target | Timeline |
|-----------|--------|----------|
| Current | ~45% | - |
| Phase 1 | 60% | 2 weeks |
| Phase 2 | 75% | 1 month |
| Phase 3 | 85% | 2 months |

---

## Running Coverage

```bash
# Generate coverage report
uv run pytest --cov=. --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Coverage for specific module
uv run pytest --cov=handlers --cov-report=term-missing tests/unit/handlers/
```
