# AEGIS CLI Quick Start Guide

## TL;DR - Your Questions Answered

### 1. Single Agent vs 3 Agents?

**Answer: Hybrid Multi-Agent with LangGraph** ✅

- **NOT** 3 completely separate agents (they'd duplicate work)
- **NOT** 1 monolithic agent (hard to debug/maintain)
- **USE**: 1 LangGraph workflow with 3 specialized sub-agents:
  - `rca_agent` (phi3:mini) → Root Cause Analysis
  - `solution_agent` (deepseek-coder) → Generate fixes
  - `verifier_agent` (llama3.1) → Verification planning

### 2. How Does Ollama Wrap K8sGPT?

**Answer: It doesn't - K8sGPT feeds data TO Ollama** ✅

```
K8sGPT (subprocess) → JSON output → Ollama agents → Analysis
```

**Flow:**
1. K8sGPT scans cluster (like `kubectl describe` but AI-powered)
2. Returns structured JSON with detected issues
3. AEGIS agents consume that JSON as context
4. Ollama models perform deep analysis on top of K8sGPT data

### 3. Output Format: Markdown? Terminal? Chat?

**Answer: Rich Terminal + Optional Markdown Export** ✅

```bash
# Command executes
aegis analyze pod/nginx-crashloop

# Output shows in terminal with Rich formatting
╭─ Root Cause Analysis ──────────────────╮
│ Issue: CrashLoopBackOff                │
│ Root Cause: Missing DATABASE_URL       │
╰────────────────────────────────────────╯

# Optional export
aegis analyze pod/nginx --export report.md
```

**NOT chat-based** - use Git-style commands instead

---

## Quick Architecture Diagram

```
User Terminal
     │
     ▼
┌─────────────────────────────────┐
│   Typer CLI (Rich formatting)   │
└──────────┬──────────────────────┘
           │
    ┌──────┴───────┐
    ▼              ▼
K8sGPT CLI    LangGraph Workflow
(subprocess)       │
    │         ┌────┴─────┬─────────┐
    │         ▼          ▼         ▼
    │    RCA Agent  Solution   Verifier
    │    (phi3)     (deepseek) (llama3)
    │         │          │         │
    └─────────┴──────────┴─────────┘
                   ▼
           Ollama Server :11434
```

---

## Example CLI Usage

```bash
# Analyze a pod
aegis analyze pod/nginx-crashloop

# Analyze with export
aegis analyze deployment/api --namespace prod --export report.md

# Auto-fix with shadow verification
aegis analyze pod/nginx --auto-fix

# Manage incidents
aegis incident list
aegis incident show inc-2024-001

# Shadow environments
aegis shadow create --name test-env
aegis shadow list
aegis shadow delete test-env
```

---

## Model Configuration

```yaml
# Your 3x 8-12GB GPUs
primary_model:
  name: "phi3:mini"
  gpu: 0
  memory: ~5GB
  use_case: RCA analysis

secondary_model:
  name: "deepseek-coder:6.7b"
  gpu: 1
  memory: ~8GB
  use_case: Solution generation

tertiary_model:
  name: "llama3.1:8b"
  gpu: 2
  memory: ~10GB
  use_case: Verification planning
```

---

## Implementation Checklist

- [ ] Install dependencies: `pip install typer rich langgraph ollama-python`
- [ ] Configure K8sGPT: `k8sgpt auth add --backend localai --baseurl http://localhost:11434/v1`
- [ ] Pull models: `ollama pull phi3:mini deepseek-coder:6.7b llama3.1:8b`
- [ ] Create CLI structure: `src/aegis/cli.py`
- [ ] Implement K8sGPT wrapper: `src/aegis/agent/analyzer.py`
- [ ] Build LangGraph workflow: `src/aegis/agent/graph.py`
- [ ] Create agent implementations: `src/aegis/agent/agents/`
- [ ] Add Rich formatters: `src/aegis/utils/formatting.py`
- [ ] Write tests: `tests/unit/test_cli.py`

---

## Testing Commands

```bash
# Test K8sGPT directly
k8sgpt analyze --filter=Pod --explain --output=json --backend=localai

# Test Ollama
ollama run phi3:mini "Analyze this error: Pod CrashLoopBackOff"

# Test CLI (once built)
python -m aegis.cli analyze pod/test-pod
```

---

## Key Files to Create

```
src/aegis/
├── cli.py                          # Main CLI entry (use Typer)
├── agent/
│   ├── graph.py                    # LangGraph workflow
│   ├── analyzer.py                 # K8sGPT wrapper
│   ├── agents/
│   │   ├── rca_agent.py           # Root Cause Analysis
│   │   ├── solution_agent.py      # Solution generation
│   │   └── verifier_agent.py      # Verification planning
│   └── llm/
│       ├── ollama.py              # Ollama client
│       └── prompts/               # Prompt templates
└── utils/
    ├── formatting.py              # Rich terminal output
    └── export.py                  # Markdown export
```

---

## Next Steps

1. **Read full architecture doc**: [CLI_LLM_INTEGRATION_ARCHITECTURE.md](./CLI_LLM_INTEGRATION_ARCHITECTURE.md)
2. **Set up environment**: Install Ollama, pull models
3. **Test K8sGPT integration**: Configure localai backend
4. **Build CLI skeleton**: Start with `cli.py` and basic commands
5. **Implement agents**: One at a time (RCA → Solution → Verifier)

---

## Questions?

Refer to the detailed architecture document for:
- Complete code examples
- LangGraph workflow implementation
- Rich terminal formatting examples
- Markdown export templates
- Testing strategies
- Common pitfalls and solutions

**Pro tip**: Start simple - get K8sGPT wrapper working first, then add one agent at a time!
