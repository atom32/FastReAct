# Multi-Line Input in FastReAct REPL

## Feature Overview

FastReAct REPL now supports multi-line input for complex queries, such as creating GitHub issues with detailed descriptions, writing code snippets, or providing long context.

---

## How to Use

### Method 1: Triple Quotes (Recommended)

Start your input with `"""` to enter multi-line mode:

```
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... Use the github create_issue tool to create an issue in atom32/FastReAct
... with title "Test GitHub MCP Integration"
... and body "Testing TODO #16: FastReAct GitHub integration
...
... This issue tests the multi-line input feature."
...
```

**End with**:
- Empty line (press Enter twice)
- Or type `'''` on a line

---

### Example: Creating GitHub Issue

```
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... Create a GitHub issue in atom32/FastReAct
... Title: "Documentation Restructuring Complete"
... Body: "Split CLAUDE.md into:
... - CLAUDE.md (rules and constraints)
... - DEVELOPMENT_LOG.md (chronological history)
...
... This improves agent context management by separating
... 'what to follow' from 'what happened'."
...
```

---

## Usage Examples

### Example 1: Code Snippets

```
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... Explain this Python code:
...
... def _resolve_command(self, command: str) -> str:
...     if os.path.isabs(command):
...         return command
...     resolved = shutil.which(command)
...     return resolved if resolved else command
...
```

### Example 2: Long-Form Context

```
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... I'm working on FastReAct, an AI agent system that uses ReAct loop.
... The system has these components:
... 1. Core Engine - manages tool execution
... 2. MCP Integration - connects to external tools
... 3. REPL - interactive shell
...
... Please suggest how to improve the tool selection logic.
...
```

### Example 3: GitHub Issue with Details

```
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... Use github create_issue for atom32/FastReAct
... Title: "Add multi-line input support to REPL"
... Body: "Currently the REPL only accepts single-line input,
... which makes it difficult to create GitHub issues with
... detailed descriptions or code snippets.
...
... Proposed solution:
... - Detect ''' as start of multi-line mode
... - Accept multiple lines until empty line
... - Pass complete text to agent
...
... This will improve UX for complex queries."
...
```

---

## Tips

1. **Copy-Paste Friendly**: Paste multi-line text directly from editor
2. **Quick Exit**: Press Enter twice (empty line) to finish
3. **Cancel**: Ctrl+C to cancel multi-line input
4. **Auto-Trim**: Leading/trailing whitespace is removed

---

## Technical Details

### Implementation

- **Detection**: Input starting with `"""` triggers multi-line mode
- **Prompt**: Changes from `>>>` to `...` to indicate continuation
- **Termination**: Empty line or `'''` ends input
- **Cross-Platform**: Works with both `prompt_toolkit` and basic input

### Code Location

File: `src/fastreact/cli/repl.py`
- `_read_multiline_input()` - prompt_toolkit implementation
- `_read_multiline_input_basic()` - basic input implementation

---

## Testing

```powershell
# Start REPL
python -m fastreact.cli.main shell

# Test multi-line
>>>
[MULTI-LINE MODE] Enter your text (end with empty line or '''):
... This is line 1
... This is line 2
... This is line 3
...
```

---

## Troubleshooting

**Issue**: Multi-line mode not triggering
- **Fix**: Ensure input starts with `"""` (three quotes)

**Issue**: Can't exit multi-line mode
- **Fix**: Press Enter twice (empty line) or type `'''`

**Issue**: Text formatting lost
- **Fix**: Empty lines are preserved, use them intentionally

---

## Future Enhancements

- [ ] Support markdown syntax highlighting in multi-line mode
- [ ] Auto-detect code blocks and apply syntax highlighting
- [ ] Edit multi-line input before submitting
- [ ] Save/load multi-line templates

---

**FastReAct REPL - Now with full multi-line support!**
