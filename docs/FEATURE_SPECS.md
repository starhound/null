# Feature Specifications

This document contains detailed design specifications for proposed Null Terminal features.

---

## 1. Smart Command Suggestions

### Overview
AI-powered command suggestions based on context, history, and current state.

### User Story
> As a user, I want intelligent command suggestions that understand my current context (directory, git status, recent commands) so I can work faster.

### Current State
- `CommandSuggester` provides static slash command suggestions
- History-based completion via arrow keys
- No contextual awareness

### Proposed Design

#### Architecture
```
┌─────────────────────────────────────────────────────────┐
│                  SuggestionEngine                       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  History    │  │  Context    │  │  AI-Powered     │  │
│  │  Provider   │  │  Provider   │  │  Provider       │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │                              │
│                    ┌─────┴─────┐                        │
│                    │  Ranker   │                        │
│                    └─────┬─────┘                        │
│                          │                              │
│                    ┌─────┴─────┐                        │
│                    │ Top N     │                        │
│                    │ Suggestions                        │
│                    └───────────┘                        │
└─────────────────────────────────────────────────────────┘
```

#### Components

**1. HistoryProvider**
```python
class HistoryProvider:
    def suggest(self, prefix: str, limit: int = 5) -> list[Suggestion]:
        """Return commands from history matching prefix."""
        # Weighted by recency and frequency
```

**2. ContextProvider**
```python
class ContextProvider:
    def suggest(self, context: ContextState) -> list[Suggestion]:
        """Suggest based on current state."""
        # - Directory contents (files suggest relevant commands)
        # - Git status (dirty repo suggests git commands)
        # - Recent errors (suggest fixes)
        # - Time of day (morning: git pull)
```

**3. AIProvider** (optional, requires AI mode)
```python
class AISuggestionProvider:
    async def suggest(self, input: str, context: ContextState) -> list[Suggestion]:
        """Use LLM to suggest contextual commands."""
        # Lightweight prompt, cached responses
```

**4. Suggestion Model**
```python
@dataclass
class Suggestion:
    command: str
    description: str
    source: Literal["history", "context", "ai"]
    score: float  # 0.0 - 1.0
    icon: str  # For display
```

#### UI Integration

```
┌─────────────────────────────────────────────┐
│ $ git sta█                                  │
├─────────────────────────────────────────────┤
│ ▸ git status         Show working tree     │
│   git stash          Stash changes         │
│   git stash pop      Apply stashed changes │
└─────────────────────────────────────────────┘
```

- Tab to accept top suggestion
- Arrow keys to navigate
- Escape to dismiss
- Inline ghost text for top suggestion

#### Configuration
```json
{
  "suggestions": {
    "enabled": true,
    "ai_enabled": false,
    "max_suggestions": 5,
    "min_chars": 2,
    "sources": ["history", "context", "ai"]
  }
}
```

#### Implementation Steps
1. Create `SuggestionEngine` base class
2. Implement `HistoryProvider` (parse command history)
3. Implement `ContextProvider` (git, files, errors)
4. Create suggestion dropdown widget
5. Add ghost text overlay to input
6. (Optional) Implement `AIProvider`

#### Effort Estimate
- Core engine: 2 days
- UI integration: 1 day
- AI provider: 1 day
- Testing: 1 day
- **Total: 5 days**

---

## 2. Conversation Branching UI

### Overview
Visual interface for exploring conversation branches and comparing AI responses.

### User Story
> As a user, I want to explore alternative AI responses by branching conversations, so I can compare different approaches without losing context.

### Current State
- `ForkRequested` message exists in `BaseBlockWidget`
- `BranchManager` tracks branches
- No visual UI for branch navigation

### Proposed Design

#### Data Model
```python
@dataclass
class ConversationBranch:
    id: str
    parent_id: str | None
    parent_block_id: str | None  # Block where branch diverged
    created_at: datetime
    name: str  # Auto-generated or user-defined
    blocks: list[BlockState]

class BranchManager:
    branches: dict[str, ConversationBranch]
    current_branch_id: str
    
    def fork(self, at_block_id: str) -> ConversationBranch
    def switch(self, branch_id: str)
    def merge(self, source_id: str, target_id: str)
    def delete(self, branch_id: str)
```

#### UI Components

**1. Branch Indicator (Status Bar)**
```
┌─────────────────────────────────────────────────────────┐
│ CLI │ main (3 branches) │ gpt-4o │ 1.2K tokens │ $0.02 │
└─────────────────────────────────────────────────────────┘
         ↑
    Click to open Branch Navigator
```

**2. Branch Navigator (Sidebar Panel)**
```
┌─────────────────────┐
│ Branches            │
├─────────────────────┤
│ ● main              │
│   └─ fix-attempt-1  │
│   └─ refactor-v2    │
│ ○ experiment        │
├─────────────────────┤
│ [+ New Branch]      │
└─────────────────────┘
```

**3. Branch Diff View (Modal)**
```
┌─────────────────────────────────────────────────────────┐
│ Compare: main ↔ fix-attempt-1                      [×]  │
├─────────────────────────────────────────────────────────┤
│ main                    │ fix-attempt-1                 │
│ ─────────────────────── │ ───────────────────────────── │
│ def process():          │ def process():                │
│   for item in items:    │   items = [x for x in        │
│     handle(item)        │            items if valid(x)]│
│                         │   for item in items:          │
│                         │     handle(item)              │
└─────────────────────────────────────────────────────────┘
```

**4. Block Fork Button**
Each AI response block gets a fork icon:
```
┌─────────────────────────────────────────────────────────┐
│ AI Response                              [↗] [📋] [🔄]  │
│                                                    ↑    │
│ Here's how to refactor...                     Fork button
└─────────────────────────────────────────────────────────┘
```

#### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+B` | Open branch navigator |
| `Ctrl+Shift+B` | Create branch at current position |
| `Alt+Left/Right` | Switch between sibling branches |

#### Implementation Steps
1. Extend `BranchManager` with full CRUD
2. Create `BranchNavigator` sidebar widget
3. Add branch indicator to `StatusBar`
4. Implement fork action in `BaseBlockWidget`
5. Create `BranchDiffScreen` modal
6. Add persistence (SQLite)
7. Testing

#### Effort Estimate
- Data model: 1 day
- BranchNavigator widget: 2 days
- Diff view: 1 day
- Integration: 1 day
- Persistence: 1 day
- **Total: 6 days**

---

## 3. Workflow Templates / Recipes

### Overview
Save and replay multi-step AI agent sessions as reusable templates.

### User Story
> As a power user, I want to save successful agent workflows as templates, so I can reuse them with different inputs.

### Current State
- Agent mode executes multi-step tasks
- Sessions can be exported to markdown
- No template/replay functionality

### Proposed Design

#### Data Model
```python
@dataclass
class WorkflowStep:
    type: Literal["prompt", "tool", "checkpoint"]
    content: str  # Prompt text or tool name
    arguments: dict  # Tool arguments or prompt variables
    expected_output: str | None  # For validation
    
@dataclass
class Workflow:
    id: str
    name: str
    description: str
    tags: list[str]
    variables: dict[str, str]  # Placeholders like {{filename}}
    steps: list[WorkflowStep]
    created_at: datetime
    source: Literal["local", "community"]
```

#### File Format (`~/.null/workflows/`)
```yaml
# debug-python.yaml
name: Debug Python Error
description: Analyze and fix Python errors with step-by-step debugging
tags: [python, debugging, fix]
variables:
  error_message: "The error you encountered"
  file_path: "Path to the file with the error"

steps:
  - type: prompt
    content: |
      Analyze this Python error:
      ```
      {{error_message}}
      ```
      In file: {{file_path}}
      
      First, read the file to understand context.
  
  - type: tool
    name: read_file
    arguments:
      path: "{{file_path}}"
  
  - type: prompt
    content: |
      Based on the file content, identify the bug and suggest a fix.
      Use write_file to apply the fix.
  
  - type: checkpoint
    content: "Confirm fix before continuing"
```

#### UI Components

**1. Workflow Browser (`/workflow` command)**
```
┌─────────────────────────────────────────────────────────┐
│ Workflows                                          [×]  │
├─────────────────────────────────────────────────────────┤
│ 🔧 Debug Python Error                                   │
│    Analyze and fix Python errors                        │
│    Tags: python, debugging                              │
│                                                         │
│ 📝 Code Review                                          │
│    Review code changes and suggest improvements         │
│    Tags: review, quality                                │
│                                                         │
│ 🚀 Deploy Checklist                                     │
│    Pre-deployment verification workflow                 │
│    Tags: devops, deploy                                 │
├─────────────────────────────────────────────────────────┤
│ [+ Create New] [Import] [Browse Community]              │
└─────────────────────────────────────────────────────────┘
```

**2. Workflow Runner**
```
┌─────────────────────────────────────────────────────────┐
│ Running: Debug Python Error                        [■]  │
├─────────────────────────────────────────────────────────┤
│ Variables:                                              │
│   error_message: [TypeError: 'NoneType' object...]      │
│   file_path: [src/parser.py                       ]     │
│                                                         │
│                              [Run Workflow]             │
└─────────────────────────────────────────────────────────┘
```

**3. Save Session as Workflow**
After successful agent session:
```
┌─────────────────────────────────────────────────────────┐
│ Save as Workflow                                   [×]  │
├─────────────────────────────────────────────────────────┤
│ Name: [                                           ]     │
│ Description: [                                    ]     │
│ Tags: [                                           ]     │
│                                                         │
│ Detected Variables:                                     │
│ ☑ filename → {{filename}}                               │
│ ☑ function_name → {{function_name}}                     │
│ ☐ specific_value (keep as-is)                           │
│                                                         │
│                      [Cancel] [Save Workflow]           │
└─────────────────────────────────────────────────────────┘
```

#### Commands
| Command | Description |
|---------|-------------|
| `/workflow` | Browse workflows |
| `/workflow run <name>` | Run a workflow |
| `/workflow save [name]` | Save current session as workflow |
| `/workflow import <file>` | Import from YAML |
| `/workflow export <name>` | Export to YAML |

#### Implementation Steps
1. Define Workflow data model
2. Create YAML parser/writer
3. Implement `WorkflowManager`
4. Build workflow browser screen
5. Create workflow runner with variable substitution
6. Add "Save as Workflow" to agent completion
7. (Future) Community workflow sharing

#### Effort Estimate
- Data model & parsing: 1 day
- WorkflowManager: 2 days
- Browser UI: 2 days
- Runner & variable substitution: 2 days
- Save from session: 1 day
- **Total: 8 days**

---

## 4. Enhanced RAG with Semantic Caching

### Overview
Improve RAG performance with SQLite-based vector storage and semantic result caching.

### User Story
> As a user with large codebases, I want faster and more accurate code search that remembers previous queries.

### Current State
- `VectorStore` uses JSON file persistence
- Pure Python cosine similarity
- No query caching
- Full re-index required for updates

### Proposed Design

#### Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    RAGManager                           │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │  QueryCache     │  │  VectorStore (SQLite)       │   │
│  │  (Semantic)     │  │  - FTS5 for text search     │   │
│  └────────┬────────┘  │  - Vector similarity        │   │
│           │           │  - Incremental updates       │   │
│           │           └─────────────────────────────┘   │
│           │                        │                    │
│           └────────────────────────┤                    │
│                                    │                    │
│                         ┌──────────┴──────────┐         │
│                         │   HybridSearch      │         │
│                         │   (Vector + FTS5)   │         │
│                         └─────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

#### SQLite Schema
```sql
-- Documents table
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings (stored as BLOB)
CREATE TABLE embeddings (
    doc_id TEXT PRIMARY KEY REFERENCES documents(id),
    vector BLOB NOT NULL,
    model TEXT NOT NULL
);

-- Full-text search
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,
    content='documents',
    content_rowid='rowid'
);

-- Query cache
CREATE TABLE query_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT,
    query_vector BLOB,
    results TEXT,  -- JSON array of doc_ids with scores
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

-- File modification tracking
CREATE TABLE file_index (
    path TEXT PRIMARY KEY,
    mtime REAL,
    hash TEXT
);
```

#### Semantic Cache
```python
class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.92):
        self.threshold = similarity_threshold
    
    async def get(self, query: str, query_vector: list[float]) -> CacheHit | None:
        """Find semantically similar cached query."""
        # 1. Hash lookup for exact match
        # 2. Vector similarity for semantic match
        # 3. Return cached results if similar enough
    
    async def set(self, query: str, query_vector: list[float], results: list):
        """Cache query results."""
```

#### Incremental Indexing
```python
class IncrementalIndexer:
    async def update(self, path: Path):
        """Update index for changed files only."""
        # 1. Scan directory for mtime changes
        # 2. Hash changed files
        # 3. Re-chunk and re-embed only changed files
        # 4. Update FTS index
```

#### Hybrid Search
```python
class HybridSearch:
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3
    ) -> list[SearchResult]:
        """Combine vector similarity with FTS5 ranking."""
        # 1. Get vector results
        # 2. Get FTS5 results
        # 3. Merge and re-rank with weights
```

#### Configuration
```json
{
  "rag": {
    "storage": "sqlite",
    "cache_enabled": true,
    "cache_similarity_threshold": 0.92,
    "cache_max_entries": 1000,
    "hybrid_search": true,
    "vector_weight": 0.7,
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

#### Implementation Steps
1. Create SQLite schema and migration
2. Implement `SQLiteVectorStore`
3. Add FTS5 integration
4. Build `SemanticCache`
5. Implement `IncrementalIndexer`
6. Create `HybridSearch`
7. Migration from JSON to SQLite
8. Performance testing

#### Effort Estimate
- SQLite schema: 1 day
- VectorStore migration: 2 days
- Semantic cache: 2 days
- Incremental indexing: 2 days
- Hybrid search: 1 day
- Testing & optimization: 2 days
- **Total: 10 days**

---

## 5. Session Sharing & Collaboration

### Overview
Share conversation sessions via URLs and enable team workspace features.

### User Story
> As a team member, I want to share my AI conversation with colleagues so we can collaborate on problem-solving.

### Current State
- Sessions export to markdown/JSON files
- No sharing mechanism
- Single-user only

### Proposed Design

#### Sharing Flow
```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────┐
│  User   │───>│  /share     │───>│  Share       │───>│  URL    │
│         │    │  command    │    │  Service     │    │ Generated
└─────────┘    └─────────────┘    └──────────────┘    └─────────┘
                                        │
                                        ▼
                               ┌──────────────────┐
                               │  Cloud Storage   │
                               │  (Optional S3)   │
                               └──────────────────┘
```

#### Share Types

**1. Public Link (Expiring)**
```
https://null.sh/s/abc123def456
```
- Read-only
- 7-day expiration (configurable)
- No authentication required

**2. Team Workspace**
```
https://null.sh/team/acme/sessions/project-debug-001
```
- Team members can view/fork
- Persistent storage
- Requires team account

**3. Self-Hosted**
```
https://your-server.com/null/s/abc123
```
- Deploy your own share server
- Full control over data

#### Data Format
```python
@dataclass
class SharedSession:
    id: str
    created_by: str
    created_at: datetime
    expires_at: datetime | None
    access_level: Literal["public", "team", "private"]
    
    # Session data (encrypted for private)
    blocks: list[BlockState]
    metadata: dict
    
    # Optional
    team_id: str | None
    fork_count: int
    view_count: int
```

#### Commands
| Command | Description |
|---------|-------------|
| `/share` | Share current session (public link) |
| `/share team` | Share to team workspace |
| `/share --expires 24h` | Share with expiration |
| `/import <url>` | Import shared session |

#### UI Components

**1. Share Dialog**
```
┌─────────────────────────────────────────────────────────┐
│ Share Session                                      [×]  │
├─────────────────────────────────────────────────────────┤
│ Visibility:                                             │
│   ○ Public (anyone with link)                           │
│   ○ Team (Acme Corp members)                            │
│   ○ Private (invite only)                               │
│                                                         │
│ Expires: [7 days ▼]                                     │
│                                                         │
│ Include:                                                │
│   ☑ Full conversation                                   │
│   ☐ Tool call results                                   │
│   ☐ Token/cost information                              │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ https://null.sh/s/abc123def456              [Copy]  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│                              [Cancel] [Create Link]     │
└─────────────────────────────────────────────────────────┘
```

**2. Shared Session Viewer**
```
┌─────────────────────────────────────────────────────────┐
│ Shared Session                          [Fork] [Import] │
│ by @user • 2 days ago • 15 views                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Read-only session view with blocks]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Backend Requirements
- Share service API (optional, can be self-hosted)
- Cloud storage for session data
- URL shortener/ID generation
- Expiration cleanup job

#### Configuration
```json
{
  "sharing": {
    "enabled": true,
    "service_url": "https://null.sh",
    "default_expiration": "7d",
    "include_tools": false,
    "self_hosted": false,
    "s3_bucket": null
  }
}
```

#### Implementation Steps
1. Define sharing protocol/format
2. Create share service API spec
3. Implement `/share` command
4. Build share dialog UI
5. Implement session viewer
6. (Optional) Self-hosted share server
7. (Optional) Team workspace features

#### Effort Estimate
- Data format: 1 day
- Share command & dialog: 2 days
- Service integration: 3 days
- Session viewer: 2 days
- Self-hosted option: 3 days
- **Total: 11 days**

---

## 6. Streaming Tool Results

### Overview
Display tool execution results in real-time rather than waiting for completion.

### User Story
> As a user running long commands via AI tools, I want to see output as it happens rather than waiting for completion.

### Current State
- Tool results shown after completion in accordion
- `run_command` waits for full output
- No streaming indication during execution

### Proposed Design

#### Streaming Architecture
```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  AI calls   │───>│  ToolRunner  │───>│  StreamingTool  │
│  tool       │    │  (async)     │    │  (PTY/Process)  │
└─────────────┘    └──────────────┘    └────────┬────────┘
                          │                     │
                          │                     │ stdout chunks
                          ▼                     ▼
                   ┌──────────────────────────────┐
                   │   ToolProgressWidget         │
                   │   (real-time output view)    │
                   └──────────────────────────────┘
```

#### Enhanced Tool Accordion
```
┌─────────────────────────────────────────────────────────┐
│ 🔧 run_command: npm install                    [▼] [■]  │
├─────────────────────────────────────────────────────────┤
│ ⏳ Running... (12s)                                     │
│ ─────────────────────────────────────────────────────── │
│ npm WARN deprecated lodash@4.17.20                      │
│ npm WARN deprecated request@2.88.2                      │
│ added 1247 packages in 10s                              │
│ █████████████████████░░░░░ 85%                          │
└─────────────────────────────────────────────────────────┘
```

#### Streaming Tool Protocol
```python
@dataclass
class ToolProgress:
    status: Literal["running", "completed", "failed", "cancelled"]
    output: str  # Cumulative output
    progress: float | None  # 0.0 - 1.0 if determinable
    elapsed: float  # Seconds
    
class StreamingTool(Protocol):
    async def execute(
        self, 
        arguments: dict,
        on_progress: Callable[[ToolProgress], None]
    ) -> str:
        """Execute tool with progress callbacks."""
```

#### Enhanced `run_command`
```python
async def run_command_streaming(
    command: str,
    working_dir: str | None = None,
    on_progress: Callable[[ToolProgress], None] | None = None
) -> str:
    """Execute command with streaming output."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=working_dir
    )
    
    output_buffer = []
    start_time = time.time()
    
    async for line in process.stdout:
        chunk = line.decode()
        output_buffer.append(chunk)
        
        if on_progress:
            on_progress(ToolProgress(
                status="running",
                output="".join(output_buffer),
                progress=None,
                elapsed=time.time() - start_time
            ))
    
    await process.wait()
    final_output = "".join(output_buffer)
    
    if on_progress:
        on_progress(ToolProgress(
            status="completed" if process.returncode == 0 else "failed",
            output=final_output,
            progress=1.0,
            elapsed=time.time() - start_time
        ))
    
    return final_output
```

#### UI Widget Updates
```python
class ToolAccordion(Widget):
    output = reactive("")
    status = reactive("pending")
    elapsed = reactive(0.0)
    
    def update_progress(self, progress: ToolProgress):
        self.output = progress.output
        self.status = progress.status
        self.elapsed = progress.elapsed
        # Auto-scroll to bottom
        self.query_one("#output").scroll_end()
```

#### Cancel Support
- Stop button on running tools
- Send SIGTERM to process
- Update AI context with "Tool cancelled by user"

#### Configuration
```json
{
  "tools": {
    "streaming_enabled": true,
    "auto_scroll": true,
    "max_output_lines": 500,
    "show_elapsed_time": true
  }
}
```

#### Implementation Steps
1. Define `ToolProgress` protocol
2. Update `run_command` with streaming
3. Modify `ToolAccordion` for live updates
4. Add cancel button functionality
5. Update AIExecutor to handle streaming tools
6. Add progress parsing for known commands (npm, pip, etc.)
7. Testing

#### Effort Estimate
- Protocol definition: 0.5 days
- Streaming run_command: 1 day
- ToolAccordion updates: 1.5 days
- Cancel support: 1 day
- Progress parsing: 1 day
- Integration: 1 day
- **Total: 6 days**

---

## Implementation Priority

Based on impact and effort:

| Priority | Feature | Effort | Impact | Recommendation |
|----------|---------|--------|--------|----------------|
| 1 | Streaming Tool Results | 6d | High | Quick win, improves UX |
| 2 | Smart Command Suggestions | 5d | High | Core usability |
| 3 | Conversation Branching | 6d | Medium | Power user feature |
| 4 | Workflow Templates | 8d | Medium | Automation value |
| 5 | Enhanced RAG | 10d | Medium | Performance |
| 6 | Session Sharing | 11d | Low* | Requires backend |

*Impact increases significantly with team adoption.

---

## Next Steps

1. Review specs with stakeholders
2. Create GitHub issues for each feature
3. Begin implementation with Priority 1-2
4. Gather user feedback on prototypes
5. Iterate based on real usage
