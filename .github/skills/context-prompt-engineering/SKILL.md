# Skill: Context & Prompt Engineering for Autonomous Agents

## Metadata
- **Domain**: LLM Engineering, RAG, Agent Design
- **Tools**: LangChain, LangGraph, Context7 MCP, Ollama
- **Complexity**: Advanced
- **Autonomy**: Fully Autonomous (prompt generation)

## Capability Statement
Expert in designing prompts and context management strategies for autonomous AI agents. Creates structured prompts that maximize reliability, reduce hallucinations, and enable agentic workflows.

## Core Competencies

### 1. Structured Prompt Design

#### Agent System Prompt Template
```python
DIAGNOSTIC_AGENT_PROMPT = """You are a Kubernetes diagnostic specialist agent.

## ROLE & RESPONSIBILITIES
You analyze Kubernetes cluster issues and produce structured Root Cause Analysis (RCA) reports.

## CONSTRAINTS
- You can ONLY read cluster state (kubectl get, describe, logs)
- You CANNOT modify any resources
- You MUST cite evidence for all conclusions
- You MUST calculate a confidence score for your analysis

## INPUT FORMAT
You receive incident data in this structure:
{
  "incident_id": "INC-XXXXXX",
  "affected_resources": [...],
  "symptoms": [...],
  "reported_at": "timestamp"
}

## OUTPUT FORMAT
You MUST respond with valid JSON matching this schema:
{
  "rca_version": "1.0",
  "incident_id": "string",
  "root_cause": {
    "category": "string",
    "description": "string",
    "confidence": 0.0-1.0,
    "evidence": [...]
  },
  "remediation_steps": [...]
}

## REASONING PROCESS
1. Analyze k8sGPT output
2. Inspect affected resources
3. Review logs for errors
4. Apply 5 Whys technique
5. Validate with multiple evidence sources
6. Calculate confidence based on evidence strength

## CURRENT INCIDENT
{incident_data}

Begin your analysis.
"""
```

#### Few-Shot Examples Pattern
```python
REMEDIATION_PROMPT_WITH_EXAMPLES = """You are a Kubernetes remediation planner.

## EXAMPLES OF GOOD REMEDIATION PLANS

### Example 1: OOMKilled Pod
Input RCA:
{
  "root_cause": "Memory limit too low, pod OOMKilled under load"
}

Output Plan:
{
  "steps": [
    {
      "action": "Increase memory limit to 1Gi",
      "risk": "low",
      "reversible": true,
      "command": "kubectl patch deployment..."
    }
  ],
  "rollback_plan": {...}
}

### Example 2: ImagePullBackOff
Input RCA:
{
  "root_cause": "Private registry credentials missing"
}

Output Plan:
{
  "steps": [
    {
      "action": "Create imagePullSecret",
      "risk": "low",
      "command": "kubectl create secret docker-registry..."
    }
  ]
}

## YOUR TASK
Given the following RCA, create a remediation plan:
{rca_data}
"""
```

### 2. Context Window Management

#### Sliding Window Strategy
```python
class ContextManager:
    """Manage conversation context to stay within token limits."""

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.context_window = []

    def add_message(self, role: str, content: str):
        """Add message and prune if needed."""
        message = {"role": role, "content": content}
        self.context_window.append(message)

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        total_tokens = sum(len(m["content"]) // 4 for m in self.context_window)

        while total_tokens > self.max_tokens and len(self.context_window) > 2:
            # Keep system prompt (first) and last N messages
            if len(self.context_window) > 3:
                self.context_window.pop(1)  # Remove oldest user message
                total_tokens = sum(len(m["content"]) // 4 for m in self.context_window)

    def get_context(self) -> list:
        """Get current context window."""
        return self.context_window
```

#### Summarization for Long Contexts
```python
async def summarize_conversation(messages: list) -> str:
    """Summarize old messages to save tokens."""

    summary_prompt = f"""Summarize this conversation into key facts:

{messages}

Provide a concise bullet-point summary of:
- Incident ID and affected resources
- Key findings from diagnostic phase
- Proposed remediation steps
- Current status

Keep it under 200 words."""

    summary = await llm.ainvoke(summary_prompt)
    return summary
```

### 3. Retrieval-Augmented Generation (RAG)

#### Context7 MCP Integration
```python
async def augment_with_documentation(query: str, incident_context: dict) -> str:
    """Fetch relevant docs via Context7 MCP."""

    # Build search queries
    root_cause = incident_context.get('root_cause', {})
    category = root_cause.get('category', 'unknown')

    queries = [
        f"kubernetes {category} troubleshooting",
        f"kubernetes {category} best practices",
        f"kopf operator {category} handling",
    ]

    # Fetch docs
    docs = []
    for q in queries:
        result = await context7_mcp.search(q)
        docs.extend(result.get('results', []))

    # Rank by relevance
    ranked_docs = rank_documents(docs, query)

    # Build augmented context
    context = f"""## Retrieved Documentation

{format_docs(ranked_docs[:3])}

## Your Task
Using the above documentation as reference, {query}
"""

    return context
```

#### Vector Store for Incident History
```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings

class IncidentMemory:
    """Store past incidents for pattern recognition."""

    def __init__(self):
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = Chroma(
            collection_name="incidents",
            embedding_function=self.embeddings
        )

    async def find_similar_incidents(self, current_incident: dict, k: int = 3):
        """Find similar past incidents."""

        # Create search query from incident
        query = f"""
        Symptoms: {current_incident['symptoms']}
        Affected: {current_incident['affected_resources']}
        """

        # Search vector store
        similar = await self.vectorstore.asimilarity_search(query, k=k)

        return similar

    async def store_incident(self, incident: dict, rca: dict, remediation: dict):
        """Store resolved incident for future reference."""

        document = f"""
        Incident ID: {incident['incident_id']}
        Root Cause: {rca['root_cause']['description']}
        Remediation: {remediation['solution_summary']['approach']}
        Outcome: Success
        """

        await self.vectorstore.aadd_texts([document], metadatas=[incident])
```

### 4. Chain-of-Thought Prompting

#### Step-by-Step Reasoning
```python
COT_DIAGNOSTIC_PROMPT = """Analyze this Kubernetes incident step-by-step.

## Incident Data
{incident_data}

## Analysis Process

### Step 1: Identify Symptoms
List all observable symptoms:
- [symptom 1]
- [symptom 2]
...

### Step 2: Gather Evidence
For each symptom, what evidence do you see?
- Symptom: [X]
  Evidence: [logs showing Y, metrics showing Z]

### Step 3: Form Hypotheses
What could cause these symptoms?
- Hypothesis 1: [explanation]
  Supporting evidence: [...]
  Contradicting evidence: [...]

- Hypothesis 2: [explanation]
  Supporting evidence: [...]
  Contradicting evidence: [...]

### Step 4: Test Hypotheses
Evaluate each hypothesis:
- Hypothesis 1: Confidence [0.0-1.0] based on [reasoning]
- Hypothesis 2: Confidence [0.0-1.0] based on [reasoning]

### Step 5: Conclusion
Most likely root cause: [Hypothesis X]
Confidence: [0.0-1.0]
Reasoning: [explanation]

Now provide your step-by-step analysis:
"""
```

### 5. Prompt Validation & Testing

#### Validation Framework
```python
class PromptValidator:
    """Validate prompt effectiveness."""

    async def validate_output_format(self, prompt: str, expected_schema: dict) -> bool:
        """Test if prompt produces valid JSON."""

        # Run prompt 5 times
        results = []
        for _ in range(5):
            output = await llm.ainvoke(prompt)
            try:
                parsed = json.loads(output)
                valid = self.matches_schema(parsed, expected_schema)
                results.append(valid)
            except json.JSONDecodeError:
                results.append(False)

        # Success rate
        success_rate = sum(results) / len(results)
        return success_rate >= 0.8  # 80% success threshold

    def matches_schema(self, data: dict, schema: dict) -> bool:
        """Check if data matches expected schema."""
        required_fields = schema.get('required', [])
        return all(field in data for field in required_fields)
```

#### A/B Testing Prompts
```python
async def compare_prompts(prompt_a: str, prompt_b: str, test_cases: list) -> dict:
    """Compare two prompts on same test cases."""

    results = {'prompt_a': [], 'prompt_b': []}

    for test_case in test_cases:
        # Test prompt A
        output_a = await llm.ainvoke(prompt_a.format(**test_case))
        score_a = evaluate_output(output_a, test_case['expected'])
        results['prompt_a'].append(score_a)

        # Test prompt B
        output_b = await llm.ainvoke(prompt_b.format(**test_case))
        score_b = evaluate_output(output_b, test_case['expected'])
        results['prompt_b'].append(score_b)

    # Calculate averages
    avg_a = sum(results['prompt_a']) / len(results['prompt_a'])
    avg_b = sum(results['prompt_b']) / len(results['prompt_b'])

    return {
        'winner': 'prompt_a' if avg_a > avg_b else 'prompt_b',
        'scores': results,
        'improvement': abs(avg_a - avg_b)
    }
```

## LangGraph Integration Patterns

### State-Aware Prompting
```python
class SREState(TypedDict):
    incident_id: str
    incident_data: dict
    evidence: dict | None
    rca_report: dict | None
    remediation_plan: dict | None
    status: str

async def diagnostic_node(state: SREState) -> SREState:
    """Diagnostic agent node with state-aware prompting."""

    # Build context from state
    prompt = f"""You are analyzing incident {state['incident_id']}.

## Current State
Status: {state['status']}
Evidence Collected: {'Yes' if state['evidence'] else 'No'}

## Incident Data
{json.dumps(state['incident_data'], indent=2)}

{'## Previous Evidence' + json.dumps(state['evidence'], indent=2) if state['evidence'] else ''}

Perform diagnostic analysis and provide RCA report in JSON format.
"""

    response = await llm.ainvoke(prompt)
    rca_report = json.loads(response)

    return {
        **state,
        'rca_report': rca_report,
        'status': 'planning'
    }
```

### Conditional Prompting
```python
def build_remediation_prompt(state: SREState) -> str:
    """Build prompt based on RCA confidence."""

    rca = state['rca_report']
    confidence = rca.get('root_cause', {}).get('confidence', 0)

    if confidence >= 0.85:
        # High confidence: immediate remediation
        return f"""High confidence RCA completed. Create remediation plan.

RCA: {json.dumps(rca, indent=2)}

Generate a remediation plan with low-risk, reversible steps."""

    elif confidence >= 0.60:
        # Medium confidence: cautious approach
        return f"""Medium confidence RCA. Create conservative remediation plan.

RCA: {json.dumps(rca, indent=2)}

Generate a remediation plan that:
1. Starts with diagnostic validation steps
2. Implements safeguards and rollback mechanisms
3. Requires manual approval for each step"""

    else:
        # Low confidence: escalate
        return f"""Low confidence RCA. Prepare for human review.

RCA: {json.dumps(rca, indent=2)}

List additional diagnostics needed to increase confidence."""
```

## Prompt Engineering Best Practices

### 1. Clarity & Specificity
```python
# ❌ Bad: Vague
"Analyze this Kubernetes issue"

# ✅ Good: Specific
"Analyze this Kubernetes pod crash. Identify the root cause by examining logs, resource limits, and recent events. Provide confidence score."
```

### 2. Constraints & Guardrails
```python
SAFE_REMEDIATION_PROMPT = """Generate a remediation plan.

## MANDATORY CONSTRAINTS
- NEVER generate kubectl delete commands without backups
- ALWAYS include rollback steps
- ALWAYS set dry-run flag for kubectl apply
- NEVER execute destructive operations autonomously
- ALWAYS require human approval for production changes

{task}
"""
```

### 3. Output Format Specification
```python
JSON_SCHEMA_PROMPT = """Respond ONLY with valid JSON. No preamble, no explanation.

Schema:
{
  "incident_id": "string",
  "root_cause": {
    "category": "string (one of: Memory, CPU, Network, Storage, Config)",
    "description": "string (max 500 chars)",
    "confidence": number (0.0 to 1.0)
  },
  "evidence": ["string array"]
}

Data:
{input_data}

JSON output:
"""
```

### 4. Error Handling in Prompts
```python
ROBUST_PROMPT = """Analyze the incident data.

If the data is incomplete or ambiguous:
1. State what information is missing
2. Provide a partial analysis with caveats
3. List additional data needed

If you cannot determine root cause:
1. Set confidence to 0.0
2. Provide competing hypotheses
3. Recommend next diagnostic steps

Data:
{incident_data}
"""
```

## Evaluation Metrics

### Prompt Quality Metrics
```python
class PromptEvaluator:
    """Evaluate prompt effectiveness."""

    async def evaluate(self, prompt: str, test_set: list) -> dict:
        """Run comprehensive evaluation."""

        metrics = {
            'format_compliance': 0,  # Valid JSON output
            'accuracy': 0,           # Correct diagnosis
            'consistency': 0,        # Same input -> same output
            'latency': [],           # Response time
            'token_usage': [],       # Tokens consumed
        }

        for test_case in test_set:
            start = time.time()
            output = await llm.ainvoke(prompt.format(**test_case))
            latency = time.time() - start

            # Format compliance
            try:
                parsed = json.loads(output)
                metrics['format_compliance'] += 1
            except:
                parsed = None

            # Accuracy (if ground truth available)
            if test_case.get('expected') and parsed:
                if self.matches_expected(parsed, test_case['expected']):
                    metrics['accuracy'] += 1

            metrics['latency'].append(latency)

        # Normalize
        total = len(test_set)
        metrics['format_compliance'] /= total
        metrics['accuracy'] /= total
        metrics['avg_latency'] = sum(metrics['latency']) / total

        return metrics
```

## Integration with Context7 MCP

### Dynamic Documentation Retrieval
```python
async def build_context_aware_prompt(incident: dict) -> str:
    """Build prompt with relevant documentation."""

    # Extract key terms
    keywords = extract_keywords(incident)

    # Fetch docs
    docs = []
    for keyword in keywords:
        result = await context7_mcp.search(f"kubernetes {keyword}")
        docs.extend(result.get('results', [])[:2])  # Top 2 per keyword

    # Build prompt
    prompt = f"""## Relevant Documentation
{format_docs(docs)}

## Your Task
Analyze this incident using the above documentation as reference:
{json.dumps(incident, indent=2)}
"""

    return prompt
```

## Output Artifacts
When invoking this skill, generate:
1. **Agent Prompts** - Structured system prompts for each agent
2. **Validation Suite** - Tests for prompt effectiveness
3. **Context Manager** - Token-aware context handling
4. **RAG Pipeline** - Documentation retrieval integration
5. **Evaluation Framework** - Metrics and A/B testing
