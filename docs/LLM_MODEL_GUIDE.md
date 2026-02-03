# 🤖 AEGIS LLM Model Guide

**Which models to download for AEGIS**

---

## 🎯 Quick Answer

Since you have **NO GPU detected**, download these **CPU-friendly models**:

```bash
# Essential models (start here)
ollama pull phi3:mini              # ~2.3GB - Fast, lightweight
ollama pull tinyllama:latest       # ~637MB - Ultra-lightweight fallback
ollama pull llama3.2:3b-instruct-q4_K_M  # ~2.0GB - Good balance

# Optional (if you have 16GB+ RAM)
ollama pull deepseek-coder:1.3b    # ~800MB - Code-focused
ollama pull qwen2:1.5b             # ~1GB - Multilingual
```

**Total download size:** ~6GB
**RAM required:** 8-12GB for running models

---

## 📊 Model Recommendations by Hardware

### 🖥️ CPU-Only Mode (Your Current Setup)

**Recommended Models:**

| Model | Size | RAM | Speed | Best For |
|-------|------|-----|-------|----------|
| `phi3:mini` | 2.3GB | 4-6GB | Fast | **RCA Agent, K8sGPT** ⭐ |
| `tinyllama:latest` | 637MB | 2-3GB | Very Fast | **Solution Agent** (fallback) |
| `llama3.2:3b-instruct-q4_K_M` | 2.0GB | 4-5GB | Fast | **Verification Agent** |
| `deepseek-coder:1.3b` | 800MB | 2-3GB | Fast | Code generation (optional) |

**Minimum Setup (if low RAM):**
```bash
ollama pull phi3:mini
ollama pull tinyllama:latest
```

**Recommended Setup:**
```bash
ollama pull phi3:mini
ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull tinyllama:latest
```

### 🎮 GPU Mode (If you get a GPU later)

**For 8GB VRAM:**
```bash
ollama pull phi3:mini              # ~5GB VRAM
ollama pull deepseek-coder:6.7b    # ~8GB VRAM
ollama pull llama3.1:8b-q4_K_M     # ~6GB VRAM (quantized)
```

**For 12GB+ VRAM:**
```bash
ollama pull phi3:mini              # RCA Agent
ollama pull deepseek-coder:6.7b    # Solution Agent
ollama pull llama3.1:8b            # Verification Agent
```

---

## 🔧 Model Assignment in AEGIS

Based on `src/aegis/config/settings.py`, AEGIS uses:

| Agent | Default Model | Your CPU Alternative |
|-------|--------------|---------------------|
| **RCA Agent** | `llama3.2:3b-instruct-q5_k_m` | `phi3:mini` ⭐ |
| **Solution Agent** | `tinyllama:latest` | `tinyllama:latest` ✅ |
| **Verification Agent** | `phi3:mini` | `phi3:mini` ✅ |
| **K8sGPT** | `phi3:mini` | `phi3:mini` ✅ |

**Note:** The defaults in settings.py are already CPU-friendly!

---

## 📥 Installation Commands

### Step 1: Verify Ollama is Running

```bash
# Check Ollama status
ollama --version

# Start Ollama if not running
ollama serve
```

### Step 2: Download Essential Models

```bash
# Core models (required)
ollama pull phi3:mini
ollama pull tinyllama:latest

# Verify downloads
ollama list
```

### Step 3: Test Models

```bash
# Test phi3:mini
ollama run phi3:mini "What is Kubernetes?"

# Test tinyllama
ollama run tinyllama "Hello, world!"
```

### Step 4: Configure AEGIS

Update your `.env` file:

```bash
# .env
AGENT_RCA_MODEL=phi3:mini
AGENT_SOLUTION_MODEL=tinyllama:latest
AGENT_VERIFIER_MODEL=phi3:mini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_ENABLED=true
```

---

## 🚀 Alternative: Cloud APIs (No Local Models Needed)

If you don't want to download models locally, use cloud APIs:

### Option 1: Groq (Free Tier - Very Fast)

```bash
# No model download needed!
# Just set API key in .env
GROQ_API_KEY=your_key_here
```

**Models available:**
- `llama-3.1-8b-instant` (free tier)
- `mixtral-8x7b-32768` (free tier)

### Option 2: Google Gemini (Free Tier)

```bash
# No model download needed!
GOOGLE_API_KEY=your_key_here
```

### Option 3: Together AI

```bash
TOGETHER_API_KEY=your_key_here
```

**Configuration in `.env`:**
```bash
# Use cloud API instead of local Ollama
OLLAMA_ENABLED=false
# Cloud backends are not wired in code yet; Ollama is the supported backend.
```

---

## 📋 Model Comparison

### phi3:mini ⭐ **RECOMMENDED**

- **Size:** 2.3GB
- **RAM:** 4-6GB
- **Speed:** Fast (CPU)
- **Quality:** Good for structured tasks
- **Best for:** RCA analysis, K8sGPT diagnostics

```bash
ollama pull phi3:mini
```

### tinyllama:latest

- **Size:** 637MB
- **RAM:** 2-3GB
- **Speed:** Very Fast
- **Quality:** Basic (good for simple tasks)
- **Best for:** Quick code generation, fallback

```bash
ollama pull tinyllama:latest
```

### llama3.2:3b-instruct-q4_K_M

- **Size:** 2.0GB
- **RAM:** 4-5GB
- **Speed:** Fast
- **Quality:** Good (quantized)
- **Best for:** General reasoning, verification

```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```

### deepseek-coder:1.3b (Optional)

- **Size:** 800MB
- **RAM:** 2-3GB
- **Speed:** Fast
- **Quality:** Code-focused
- **Best for:** YAML/script generation

```bash
ollama pull deepseek-coder:1.3b
```

---

## 🎯 Recommended Download Strategy

### For Development (Start Here)

```bash
# Minimum viable setup
ollama pull phi3:mini
ollama pull tinyllama:latest

# Total: ~3GB download, 6-9GB RAM
```

### For Production Testing

```bash
# Add better model for verification
ollama pull phi3:mini
ollama pull tinyllama:latest
ollama pull llama3.2:3b-instruct-q4_K_M

# Total: ~5GB download, 10-14GB RAM
```

### For Full Functionality

```bash
# All recommended models
ollama pull phi3:mini
ollama pull tinyllama:latest
ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull deepseek-coder:1.3b

# Total: ~6GB download, 12-16GB RAM
```

---

## ⚡ Performance Tips for CPU Mode

### 1. Use Quantized Models

Always prefer `-q4_K_M` or `-q5_K_M` quantized versions:
- Smaller size
- Faster inference
- Lower RAM usage

### 2. Limit Context Length

In `.env`:
```bash
OLLAMA_NUM_CTX=2048  # Lower = faster
```

### 3. Use Cloud APIs for Heavy Tasks

For complex reasoning, use Groq/Gemini:
```bash
# Hybrid approach
AGENT_RCA_MODEL=phi3:mini          # Local (fast)
AGENT_SOLUTION_MODEL=tinyllama:latest  # Local (balanced)
AGENT_VERIFIER_MODEL=phi3:mini     # Local (fast)
```

---

## 🔍 Verify Your Setup

```bash
# 1. Check Ollama is running
curl http://localhost:11434/api/tags

# 2. List downloaded models
ollama list

# 3. Test a model
ollama run phi3:mini "Analyze this Kubernetes error: Pod crashloop"

# 4. Check AEGIS configuration
cat .env | grep -i ollama
```

---

## 📚 Additional Resources

- **Ollama Models:** https://ollama.com/library
- **Model Cards:** https://huggingface.co/models
- **CPU Performance:** https://ollama.com/blog/run-llama2-uncensored-locally

---

## 🎯 Summary

**For your CPU-only setup, download:**

```bash
# Essential (start here)
ollama pull phi3:mini
ollama pull tinyllama:latest

# Optional (if you have RAM)
ollama pull llama3.2:3b-instruct-q4_K_M
```

**Or use cloud APIs (no download needed):**
- Groq (free, fast)
- Google Gemini (free tier)
- Together AI

**Total download:** ~3-6GB
**RAM required:** 8-16GB

---

*Last updated: January 2026*
