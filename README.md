# Visual CrewAI Agent & Workflow Builder (No-Code CLI Orchestrator)

A modern, developer-friendly web application and local CLI pipeline that allows anyone to visually construct, configure, validate, and generate production-ready **CrewAI** multi-agent workflows without writing boilerplate code.

---

## 🌟 Key Features

### 1. Interactive Node-Based Visual Canvas
- **Pan & Zoom Navigation**: Smooth infinite canvas with mouse wheel zoom, click-and-drag panning, and reset/fit controls.
- **Grid Snapping**: 20px magnetic grid snapping toggle for crisp node alignment.
- **Interactive Minimap**: Real-time picture-in-picture canvas preview with interactive camera viewport navigation.
- **Specialized Node Architecture**:
  - 🤖 **Agent Node**: Define Role, Goal, Backstory, LLM Provider, Temperature, Max Iterations, and toggles for Delegation, Memory, and Verbose logging.
  - ⚡ **Task Node**: Description prompts, Expected Output format, Assigned Agent, Asynchronous execution toggle, and Output File path.
  - 🛠️ **Tool Node**: Pre-built tools including Google Search (`SerperDevTool`), Website Scraper (`ScrapeWebsiteTool`), Directory Reader (`DirectoryReadTool`), File Reader (`FileReadTool`), and Custom `@tool` Python functions.
  - 👥 **Crew Config Node**: Orchestration process (`Sequential` vs. `Hierarchical`), Manager LLM, Memory vector toggles, Cache, and RPM limits.
- **Dynamic Bezier Flow Connectors**: Interactive port handles with cubic bezier curves showing data flow between Tools, Agents, and Tasks.

### 2. Node Property Inspector / Sidebar
- Dedicated right-hand drawer that opens on selecting or editing any node.
- Model picker supporting:
  - **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `o1-preview`, `o1-mini`
  - **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229`
  - **Google Gemini**: `gemini/gemini-1.5-pro`, `gemini/gemini-1.5-flash`
  - **Groq**: `groq/llama-3.3-70b-versatile`, `groq/llama-3.1-8b-instant`
  - **Local Ollama (Offline)**: `ollama/llama3.2:latest`, `ollama/mistral:latest`, `ollama/deepseek-r1:latest`
- Slider controls for Temperature and Max Iterations.
- Instant reactive updates across canvas badges and code viewer.

### 3. Real-Time Dual Code Generator
- Live split-view code drawer updating in real-time as nodes and properties change:
  - **Tab 1: Native CrewAI Project Structure** (`config/agents.yaml`, `config/tasks.yaml`, `crew.py`, `main.py`).
  - **Tab 2: Single-File Executable Script** (`crew_runner.py`) for immediate `python crew_runner.py` execution.
  - **Tab 3: Environment Config** (`.env`) with auto-detected API keys.
  - **Tab 4: Dependency Spec** (`requirements.txt`).
- One-click file download and copy-to-clipboard buttons.
- Full **Export ZIP** packaging that downloads a turnkey CrewAI repository.

### 4. Direct CLI & Terminal Integration Assistant
- Built-in CLI Wizard modal with copyable, tailored commands for **Windows PowerShell** and **macOS/Linux Bash**.
- **Interactive Terminal Dry-Run Simulator**: Runs validation checks on the graph (missing agents, circular references, manager LLMs) and simulates runtime execution step-by-step.
- Full standalone command-line orchestrator via `python cli.py`.

---

## 🚀 Getting Started

### Method 1: Launch Local Web Studio
Run the included development server:
```bash
python server.py
```
Open **`http://localhost:8080`** in your browser to start visually designing your crew workflows!

---

### Method 2: Command-Line CLI Pipeline
The `cli.py` utility allows you to inspect, validate, and generate CrewAI projects directly from your terminal:

#### 1. List Available Workflow Templates
```bash
python cli.py list-templates
```

#### 2. Validate a Workflow JSON
```bash
python cli.py validate templates/market_research.json
```

#### 3. Generate a Complete CrewAI Project on Disk
```bash
python cli.py generate templates/market_research.json --out-dir ./my_market_crew
```
This generates:
- `my_market_crew/config/agents.yaml`
- `my_market_crew/config/tasks.yaml`
- `my_market_crew/crew_runner.py`
- `my_market_crew/.env`
- `my_market_crew/requirements.txt`

#### 4. Run the Generated Crew
```bash
cd my_market_crew
pip install -r requirements.txt
python crew_runner.py
```

---

## 📁 Project Structure

```
CrewAI_agent/
├── index.html               # Main visual workspace application
├── css/
│   └── style.css            # Dark-theme design system and UI components
├── js/
│   ├── app.js               # Application coordinator and event manager
│   ├── canvas.js            # Pan/zoom, bezier curves, drag-and-drop canvas engine
│   ├── nodes.js             # Node data models, schemas, and LLM catalog
│   ├── inspector.js         # Reactive right-hand property sidebar
│   ├── generator.js         # Real-time CrewAI YAML and Python code generator
│   ├── templates.js         # Curated workflow templates
│   ├── cli-wizard.js        # Terminal wizard and dry-run execution simulator
│   └── exporter.js          # ZIP packaging and JSON import/export
├── docs/                    # Automated Living Documentation System
│   ├── architecture/        # Zero-drift active architecture & data schemas
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   └── DATA_SCHEMAS.md
│   ├── flows/               # Active technical process & runtime flows
│   │   ├── WORKFLOW_ORCHESTRATION_FLOW.md
│   │   └── AGENT_EXECUTION_FLOW.md
│   ├── requirements/        # Machine-readable specification registry
│   │   └── SPEC_REGISTRY.json
│   └── CHANGELOG_REQUIREMENTS.md # Reverse-chronological requirements audit trail
├── scripts/
│   └── doc_pipeline.py      # Documentation automation, sync & validation pipeline
├── .github/workflows/
│   └── docs-automation.yml  # CI/CD automated documentation synchronization
├── .githooks/
│   └── pre-commit           # Pre-commit hook for local zero-drift verification
├── assets/                  # Offline bundled Prism and JSZip assets
├── templates/               # Sample JSON workflow definitions
├── server.py                # Lightweight local web server
├── cli.py                   # Command-line workflow generator & validator
└── README.md                # Documentation & usage guide
```

---

## 📚 Living Documentation & Auto-Changelog Pipeline

This repository features a self-updating, zero-drift documentation pipeline:

### 1. Zero-Drift Architecture & Technical Flows
- `/docs/architecture/` and `/docs/flows/` dynamically reflect only the **active** codebase. Deprecated paths and abandoned modules are automatically pruned during synchronization.

### 2. Reverse-Chronological Requirements Changelog
- All business requirements, user stories, implementation summaries, and architectural impacts are audited in `/docs/CHANGELOG_REQUIREMENTS.md` with the newest updates on top.

### 3. Pipeline CLI Commands
```bash
# Validate documentation consistency and integrity
python scripts/doc_pipeline.py validate

# Synchronize active architecture with current codebase modules
python scripts/doc_pipeline.py sync-architecture

# Programmatically record a new development stage / requirement
python scripts/doc_pipeline.py record-change \
  --stage-id STAGE-003 \
  --version 1.2.0 \
  --title "Custom Webhook Integrations" \
  --req "Enable agents to trigger arbitrary external webhooks" \
  --user-story "As a developer, I want agents to dispatch HTTP POST payloads upon task completion" \
  --summary "Added WebhookTool node and async callback dispatcher" \
  --impact "Extended Tool schema and added webhook payload dispatch to generator" \
  --files js/nodes.js js/generator.js
```

### 4. Git Hooks & CI/CD Setup
- **Enable Local Pre-Commit Hook**:
  ```bash
  git config core.hooksPath .githooks
  ```
- **GitHub Actions Automation**:
  `.github/workflows/docs-automation.yml` triggers on pushes/PRs to `main`, runs zero-drift verification, and automatically commits updated documentation back to the repository with `[skip ci]`.

---

## 🔒 Privacy & Local Ollama Support
The builder includes native presets and configuration for **100% offline, local execution** using [Ollama](https://ollama.ai). Select `Ollama (Local Offline)` as your provider to build completely private agent crews requiring zero external cloud API keys!
