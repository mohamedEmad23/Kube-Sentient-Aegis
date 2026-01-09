# 🚀 Quick Start Guide for Data Scientists (No GPU)

## Your Profile
- **Hardware**: Intel Iris Xe, 40GB RAM
- **Ollama**: Installed ✅
- **Model**: llama3.1 (but should switch to smaller)
- **Status**: Ready to start!

---

## Step 1: Optimize Your Setup (15 minutes)

### Configure Ollama for CPU Performance

```bash
# 1. Check current Ollama status
ollama list

# 2. Pull CPU-optimized models (quantized, faster on CPU)
ollama pull llama3.2:3b-q4_0    # 2GB - RECOMMENDED FOR YOU
ollama pull phi3:mini            # 2.3GB - Great reasoning
ollama pull tinyllama:1b         # 700MB - Super fast testing

# 3. Remove large models to save space (optional)
ollama rm llama3.1               # If you have the 8B version (5GB)

# 4. Test performance
time ollama run llama3.2:3b-q4_0 "Explain Kubernetes pods in 2 sentences"
# Should take 5-15 seconds on your CPU
```

### Set CPU Thread Count

```bash
# Add to your ~/.bashrc or ~/.zshrc
export OLLAMA_NUM_THREADS=8      # Use 8 of your CPU threads
export OLLAMA_MAX_LOADED_MODELS=1  # Load only 1 model at a time

# Reload shell
source ~/.bashrc
```

---

## Step 2: Test the Ollama Client (30 minutes)

### Install Dependencies

```bash
cd /home/mohammed-emad/VS-CODE/unifonic-hackathon

# Activate virtual environment (if using uv)
source .venv/bin/activate

# Or install with pip
pip install httpx pydantic
```

### Run the Test Example

```bash
# Run the basic test script
python examples/test_ollama_basic.py
```

**Expected output:**
```
🔧 Testing Ollama Integration
============================================================
1️⃣ Checking Ollama server health...
✅ Ollama server is healthy
2️⃣ Listing available models...
✅ Found 3 model(s):
   • llama3.2:3b-q4_0 (2.0GB)
   • phi3:mini (2.3GB)
   • tinyllama:1b (0.7GB)
...
```

---

## Step 3: Run Unit Tests (15 minutes)

```bash
# Run tests for Ollama client
pytest tests/unit/test_ollama.py -v

# Expected: All tests pass ✅
```

---

## Step 4: Your First Integration Task (2-3 hours)

**Goal**: Create a prompt template system for Kubernetes incident analysis

### Task Breakdown

**File to create**: `src/aegis/agent/prompts/system.py`

```python
"""System prompts for AEGIS incident analysis."""

SYSTEM_PROMPT_SRE = """You are AEGIS, an expert Kubernetes SRE agent.
Your role is to analyze incidents, diagnose root causes, and propose fixes.
Always think step-by-step and verify your reasoning."""

INCIDENT_ANALYSIS_TEMPLATE = """Analyze this Kubernetes incident:

**Incident Details:**
- Pod: {pod_name}
- Namespace: {namespace}
- Status: {status}
- Error Message: {error_message}

**Recent Logs:**
{logs}

**Task:**
1. Identify the root cause
2. Assess the severity (Critical/High/Medium/Low)
3. Propose a fix
4. List verification steps

Respond in JSON format:
{{
  "root_cause": "...",
  "severity": "...",
  "proposed_fix": "...",
  "verification_steps": ["step1", "step2"]
}}
"""

MEMORY_LEAK_TEMPLATE = """A pod is showing signs of a memory leak:

**Pod**: {pod_name}
**Namespace**: {namespace}
**Memory Usage**: {memory_usage}
**Memory Limit**: {memory_limit}
**Uptime**: {uptime}

Analyze if this is a genuine memory leak and suggest remediation.
"""

SQL_INJECTION_TEMPLATE = """Potential SQL injection detected:

**Endpoint**: {endpoint}
**Payload**: {payload}
**Log Entry**: {log_entry}

1. Verify if this is a true SQL injection attempt
2. Suggest WAF rules to block it
3. Provide a secure code fix
"""
```

### Implementation Steps

1. Create the prompts file ✅ (done above)
2. Write tests for prompt templating
3. Integrate with OllamaClient
4. Test with real Kubernetes error examples

---

## Step 5: Performance Benchmarking (1 hour)

**Goal**: Measure inference time on your CPU

Create `examples/benchmark_cpu_inference.py`:

```python
import asyncio
import time
from aegis.agent.llm import OllamaClient, OllamaConfig

async def benchmark():
    """Benchmark different models on CPU."""
    models = ["llama3.2:3b-q4_0", "phi3:mini", "tinyllama:1b"]
    prompt = "Explain Kubernetes pods in 2 sentences."

    for model in models:
        config = OllamaConfig(model=model)
        client = OllamaClient(config)

        # Warmup
        await client.generate(prompt)

        # Benchmark 5 runs
        times = []
        for i in range(5):
            start = time.time()
            await client.generate(prompt)
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)
        print(f"{model}: {avg_time:.2f}s average")

        await client.close()

asyncio.run(benchmark())
```

**Run it**:
```bash
python examples/benchmark_cpu_inference.py
```

**Expected results** (on your CPU):
```
llama3.2:3b-q4_0: 8.2s average  ✅ Best balance
phi3:mini: 12.5s average         ⚠️ Slower but better reasoning
tinyllama:1b: 3.1s average       ✅ Super fast for testing
```

---

## Step 6: Alternative - Use Free Cloud APIs (1 hour)

**If CPU is too slow**, use free cloud APIs (NO credit card needed):

### Option A: Groq (RECOMMENDED - Fastest)

```bash
# 1. Get free API key (30 seconds)
# → https://console.groq.com/keys
# No credit card, instant activation

# 2. Add to .env
echo "GROQ_API_KEY=gsk_xxxxx" >> .env

# 3. Test it
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Option B: Google Gemini

```bash
# 1. Get free API key
# → https://aistudio.google.com/apikey

# 2. Add to .env
echo "GOOGLE_API_KEY=xxxxx" >> .env
```

---

## What to Learn Next (Week 1 Goals)

### Day 1-2: Ollama Basics ✅
- [x] Optimize CPU configuration
- [x] Test OllamaClient
- [x] Run unit tests
- [x] Benchmark performance

### Day 3-4: Prompt Engineering
- [ ] Create prompt templates
- [ ] Test with K8s error examples
- [ ] Measure accuracy of responses

### Day 5: Integration
- [ ] Connect prompts + OllamaClient
- [ ] Build simple CLI: `aegis analyze <pod-name>`
- [ ] Test end-to-end workflow

---

## Learning Resources

### Ollama Documentation
- Official docs: https://ollama.com/library
- Model library: https://ollama.com/library
- API reference: https://github.com/ollama/ollama/blob/main/docs/api.md

### Python AsyncIO (Required for this codebase)
- Tutorial: https://realpython.com/async-io-python/
- Httpx docs: https://www.python-http.org/en/stable/

### LangChain/LangGraph (Next week)
- LangGraph tutorial: https://langchain-ai.github.io/langgraph/tutorials/introduction/
- Ollama integration: https://python.langchain.com/docs/integrations/chat/ollama/

---

## Troubleshooting

### "Ollama server not running"
```bash
# Start Ollama
ollama serve

# Or check if already running
ps aux | grep ollama
```

### "Model not found"
```bash
# Pull the model
ollama pull llama3.2:3b-q4_0

# List installed models
ollama list
```

### "Too slow on CPU"
```bash
# Switch to free cloud APIs (see Step 6)
# OR use smaller model
ollama pull tinyllama:1b  # 700MB, very fast
```

### "Import errors"
```bash
# Install dependencies
pip install httpx pydantic pytest pytest-asyncio

# Or use uv
uv pip install httpx pydantic pytest pytest-asyncio
```

---

## Daily Progress Checklist

**Day 1** (Today):
- [ ] Configure Ollama for CPU ✅
- [ ] Run `examples/test_ollama_basic.py` ✅
- [ ] Run `pytest tests/unit/test_ollama.py` ✅
- [ ] Benchmark CPU performance

**Day 2**:
- [ ] Read LangChain docs
- [ ] Create prompt templates
- [ ] Write tests for prompts

**Day 3**:
- [ ] Integrate prompts + OllamaClient
- [ ] Test with real K8s errors
- [ ] Measure response quality

**Day 4**:
- [ ] Build simple CLI tool
- [ ] Test end-to-end workflow
- [ ] Document your work

**Day 5**:
- [ ] Code review with team
- [ ] Optimize performance
- [ ] Plan next week's tasks

---

## Questions to Ask Team

1. **GPU teammates**: What models are they using? Can you share inference times?
2. **Security engineer**: What security scenarios should we prioritize?
3. **Lead**: Should we focus on Ollama or free APIs for development?

---

## Success Metrics

By end of Week 1, you should:
- ✅ Have working Ollama client
- ✅ Understand async Python patterns
- ✅ Created prompt templates
- ✅ Benchmarked CPU vs cloud APIs
- ✅ Built a simple demo CLI

**You're ready to start! Run the test example first** 🚀
