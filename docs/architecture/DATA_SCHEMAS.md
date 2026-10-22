# Data Schemas & Serialization Contracts

> **Auto-Generated & Synchronized Document**  
> **Source of Truth Policy**: Reflects the active data structures implemented in `js/nodes.js` and `cli.py`.

---

## 1. Node Data Models

### 1.1 Agent Node (`agent`)
```typescript
interface AgentNode {
  id: string;               // Unique ID: 'agent_<timestamp>_<random>'
  type: 'agent';
  x: number;                // World coordinate X
  y: number;                // World coordinate Y
  name: string;             // Variable name (e.g., 'Lead_Researcher')
  role: string;             // Agent role title
  goal: string;             // Primary agent objective
  backstory: string;        // Agent prompt persona
  llm_provider: string;     // 'OpenAI' | 'Anthropic' | 'Google Gemini' | 'Groq' | 'Ollama'
  model_name: string;       // Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet')
  temperature: number;      // 0.0 to 1.0 (default: 0.7)
  verbose: boolean;         // Stream reasoning to console
  allow_delegation: boolean;// Enable subtask delegation
  memory: boolean;          // Enable short/long-term memory
  max_iter: number;         // Maximum reasoning loops (default: 25)
  tools: string[];          // Connected Tool Node IDs
}
```

### 1.2 Task Node (`task`)
```typescript
interface TaskNode {
  id: string;               // Unique ID: 'task_<timestamp>_<random>'
  type: 'task';
  x: number;
  y: number;
  name: string;             // Task identifier
  title: string;            // User-friendly display title
  description: string;      // Task prompt instructions
  expected_output: string;  // Explicit evaluation criteria
  agent_id: string | null;  // Explicit assigned Agent ID
  async_execution: boolean; // Run concurrently
  output_file: string;      // Export path (e.g., 'report.md')
  human_input: boolean;     // Pause for human-in-the-loop review
  depends_on: string[];     // Prior Task IDs
}
```

### 1.3 Tool Node (`tool`)
```typescript
interface ToolNode {
  id: string;               // Unique ID: 'tool_<timestamp>_<random>'
  type: 'tool';
  x: number;
  y: number;
  tool_type: 'SerperDevTool' | 'ScrapeWebsiteTool' | 'DirectoryReadTool' | 'FileReadTool' | 'CSVSearchTool' | 'WebsiteSearchTool' | 'CustomPythonTool';
  name: string;             // Display label
  api_key_env: string | null;// Required env key (e.g., 'SERPER_API_KEY')
  parameters: Record<string, any>;
  custom_code?: string;     // Python source code for @tool functions
}
```

### 1.4 Crew Configuration Node (`crew`)
```typescript
interface CrewConfigNode {
  id: string;               // Unique ID: 'crew_<timestamp>_<random>'
  type: 'crew';
  x: number;
  y: number;
  name: string;             // Crew class name
  process: 'sequential' | 'hierarchical';
  manager_llm: string | null; // Required if process === 'hierarchical'
  memory: boolean;          // Shared crew vector memory
  verbose: number;          // 1 (Standard) or 2 (Detailed)
  cache: boolean;           // Cache tool execution results
  max_rpm: number;          // Request rate limiting
}
```

---

## 2. Connection Topology Rules

| Source Node | Source Port | Target Node | Target Port | Connection Type | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tool** | `output` (Right) | **Agent** | `input` (Left) | `tool-agent` | Attaches search/scrape/file capability to agent |
| **Agent** | `output` (Right) | **Task** | `input` (Left) | `agent-task` | Assigns responsible agent to execute task |
| **Task** | `output` (Right) | **Task** | `input` (Left) | `task-task` | Establishes sequential task pipeline dependency |
