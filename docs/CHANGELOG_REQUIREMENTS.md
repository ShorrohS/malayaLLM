# Requirements & Development Historical Audit Trail (Changelog)

> **Traceability & Governance Policy**:
> - All requirements, architectural enhancements, and development stages are maintained here in **reverse-chronological order** (newest updates at the top).
> - New entries are automatically generated and prepended by the documentation automation pipeline (`scripts/doc_pipeline.py`).
> - Historical entries are strictly immutable to preserve complete decision auditability.

---

<!-- AUTO_CHANGELOG_START -->

## [STAGE-007] v2.3.0 — Autonomous, Lightweight Modular Malayalam Data Pipeline & Operations Center
*Recorded: 2026-10-22 11:05:00 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Replace heavy agent framework dependencies with a high-performance, pure Python modular backend engine and a responsive, zero-bloat vanilla ES6 web Operations Center. Provide 100% offline capability (via local Ollama daemon and deterministic linguistic heuristics) alongside multi-provider API key rotation (Groq, Gemini, OpenRouter, NVIDIA NIM) with automatic HTTP 429 hot-swap error handling, continuous autonomous harvesting, morphological cleaning, and human-in-the-loop review.
- **User Story**: As an NLP researcher and ML engineer curating low-resource Dravidian datasets, I want an autonomous, zero-bloat pipeline running on pure Python and SQLite WAL ledger with real-time Play/Pause/Step controls, side-by-side text inspection, Unicode density gating, and instant export to Google Colab QLoRA scripts, so that I can reliably curate high-quality Malayalam corpora in both air-gapped and cloud environments.

### 2. Development Implementation Summary
- **SQLite Job State & Ledger (`backend/db.py`)**: Designed `pipeline_state.db` tracking run states, iteration counts, stage statuses, event logs, live item streaming, and the Human Review Queue with automatic seeding.
- **Multi-Key Fallback & Rotation Engine (`backend/key_rotator.py`)**: Built credential manager with round-robin pooling, 429 rate-limit backoff cooldowns, persistent vault storage (`data/keys_vault.json`), and cascade failover across Groq, Gemini, OpenRouter, NVIDIA NIM, and local Ollama (`http://localhost:11434`).
- **Decoupled Modular Python Pipeline (`backend/pipeline_engine.py` & `workers/*`)**:
  - `workers/ingestor.py`: Standalone non-blocking harvester reading from local files, Malayalam RSS feeds, and offline Dravidian archives.
  - `workers/normalizer.py`: Morphological cleaner enforcing NFKC normalization, atomic Chillu standardization (ൺ, ൻ, ർ, ൽ, ൾ, ൿ), HTML/URL stripping, Indian PII redaction, and ≥60% Malayalam Unicode density gating (`\u0D00-\u0D7F`).
  - `workers/judge.py`: Quality judge using rotating LLMs with fallback to deterministic Dravidian linguistic critic to evaluate syntax and drop machine translationese.
  - `workers/exporter.py`: Bundles approved items into JSONL, structured JSON, and Google Colab Unsloth QLoRA training script with Google Drive 50-step checkpoint relay loop.
- **FastAPI Operations Center Server (`server.py`)**: REST endpoints (`/api/pipeline/start`, `/api/pipeline/pause`, `/api/pipeline/step`, `/api/pipeline/status`, `/api/queue/review`, `/api/queue/action`, `/api/keys`, `/api/export/trigger`, `/api/health`).
- **Web Operations Center UI (`index.html`, `js/dashboard.js`, `css/operations.css`)**: Master Play/Pause control with real-time state sync, visual 4-node animated diagram with pulsing status rings and stage progress bars, live side-by-side item inspector with density gauges, and interactive Human Review Queue.

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Eliminates framework bloat in favor of a clean, decoupled Python worker architecture with SQLite WAL persistence, strict UTF-8 enforcement across all I/O to eliminate Malayalam Mojibake, and instant Google Colab fine-tuning handoff.
- **Files Modified/Created**:
  - `backend/db.py`
  - `backend/key_rotator.py`
  - `backend/pipeline_engine.py`
  - `workers/ingestor.py`
  - `workers/normalizer.py`
  - `workers/judge.py`
  - `workers/exporter.py`
  - `server.py`
  - `index.html`
  - `css/operations.css`
  - `js/dashboard.js`
  - `docs/CHANGELOG_REQUIREMENTS.md`

---

## [STAGE-006] v2.2.0 — Malayalam End-to-End Autonomous Scraping, Human-Approval & Colab Training Pipeline
*Recorded: 2026-10-22 10:47:23 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Build an end-to-end multi-agent pipeline and Operations Center extension for Malayalam corpus collection, NFKC and atomic chillu normalization, LLM-as-a-judge quality critique, human-in-the-loop review queue, multi-key round-robin/fallback rotation engine, and Google Colab QLoRA/Unsloth training handoff bridge.
- **User Story**: As an NLP engineer working with low-resource Indian languages, I want an autonomous scraping and morphological normalization workflow with human-in-the-loop batch verification and instant Google Colab checkpoint-relay training script export, so that I can collect high-purity Malayalam pre-training and instruction datasets without losing GPU progress.

### 2. Development Implementation Summary
- Engineered utils/key_rotator.py with multi-key round-robin rotation, 429 rate-limit backoff, and provider cascade fallback. Implemented utils/malayalam_cleaner.py featuring NFKC normalization, atomic Chillu standardization, HTML stripping, Indian PII redaction, Malayalam unicode density gating (>=60%), and translationese heuristic evaluation. Created utils/colab_trainer_loader.py providing standalone Unsloth/PEFT QLoRA script with Google Drive checkpoint relay loop to bypass Colab 12-hour session timeouts. Built Operations Center Dataset Review Queue and Colab Training Bridge UI tabs with side-by-side comparison, density meters, approve/reject state transitions, and server.py REST endpoints (/api/dataset/*, /api/training/*, /api/key_rotator/*).

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Transforms Visual CrewAI Studio into an enterprise-grade NLP corpus curation platform with multi-key API resilience, strict Dravidian linguistic normalization, human-in-the-loop dataset review, and direct training handoff to Google Colab and Kaggle.
- **Files Modified/Created**:
  - `utils/key_rotator.py`
  - `utils/malayalam_cleaner.py`
  - `utils/colab_trainer_loader.py`
  - `utils/seed_dataset.py`
  - `js/dataset-review.js`
  - `js/templates.js`
  - `js/nodes.js`
  - `js/key-vault.js`
  - `js/generator.js`
  - `js/app.js`
  - `index.html`
  - `css/style.css`
  - `server.py`

---
## [STAGE-005] v2.1.0 — Responsive Layout Viewport Overflow Fixes and Default 100% Offline Ollama Template
*Recorded: 2026-10-21 07:32:32 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Resolve viewport responsive breakages across desktop, tablet, and mobile displays with collapsible header controls, fluid docked panels, and zero horizontal scrolling. Pre-load the 100% Offline Ollama Crew template by default on initial application boot for instant simulation readiness without cloud API credentials.
- **User Story**: As an AI engineer or enterprise developer working in on-premise air-gapped environments, I want the web application to adapt fluidly to any screen resolution and immediately boot into a functioning 100% local Ollama agent workflow so that I can visually configure and simulate multi-agent crews without setup friction or credential prerequisites.

### 2. Development Implementation Summary
- Implemented strict flexbox/grid constraints with overflow-x: hidden and min-width: 0 across .app-container, .top-nav, canvas container, and docked drawers. Added collapsible header controls with an overflow dropdown menu for secondary actions (Snap, Fit, Zoom, JSON load/save, Clear) on screens below 992px while preserving persistent visibility of Ollama status and Key Vault pills. Added responsive drawer toggle for the left components panel with Ctrl+B shortcut. Configured WORKFLOW_TEMPLATES.offline_ollama with Local Research Specialist, Synthesis Task, and PrivateLocalCrew as default initial workflow, and enriched terminal dry-run sandbox with local daemon verification.

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Ensures robust cross-resolution responsiveness with zero horizontal viewport overflow. Delivers a zero-friction out-of-the-box experience where new sessions automatically load a private local Ollama pipeline ready for immediate in-browser dry-run simulation.
- **Files Modified/Created**:
  - `index.html`
  - `css/style.css`
  - `js/templates.js`
  - `js/cli-wizard.js`
  - `js/app.js`

---
## [STAGE-004] v2.0.0 — Professional Operations Center & Live Key Vault Release
*Recorded: 2026-10-21 06:59:07 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Redesign the application into a function-first Professional Operations Center with persistent status badges, real-time Ollama auto-discovery, live API key vault, and network/topology diagnostics.
- **User Story**: As an enterprise AI developer, I want a high-density, function-first workspace with live Ollama model auto-discovery, interactive diagnostics with click-to-fix links, visual error boundaries, and instant API key sync to .env.

### 2. Development Implementation Summary
- Engineered unified KeyVault manager (js/key-vault.js) with Ollama model auto-discovery and live format validation; built DiagnosticsManager (js/diagnostics.js) for topology audits; redesigned index.html with persistent utility header, search-filterable accordion sidebar (Ctrl+K), high-contrast dot-matrix canvas (#FAFAFA/#E5E7EB), structured node data rows with error boundary warning banners; integrated dock with live Code Exporter, CLI Assistant, and Diagnostics Console; updated server.py with Ollama proxy.

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Added KeyVault and DiagnosticsManager to system architecture; added Ollama proxy to local server; transformed UI into an enterprise operations center.
- **Files Modified/Created**:
  - `index.html`
  - `css/style.css`
  - `js/app.js`
  - `js/canvas.js`
  - `js/key-vault.js`
  - `js/diagnostics.js`
  - `js/generator.js`
  - `server.py`

---
## [STAGE-003] v1.2.0 — Warm Minimalist / Modern SaaS Workspace Redesign
*Recorded: 2026-10-21 05:48:28 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Redesign the application from dark sci-fi into a clean, inviting Warm Minimalist SaaS workspace inspired by Linear, Notion, and Raycast.
- **User Story**: As a developer and designer, I want an inviting warm off-white workspace with soft natural shadows, terracotta primary accents, sage/amber/slate semantic node badges, and light theme syntax highlighting.

### 2. Development Implementation Summary
- Overhauled css/style.css with warm cream canvas (#FBFBF9), subtle grid dots (#EAE8E4), pure white cards with soft multi-layered shadows and crisp borders (#E5E3DE), terracotta accent (#D95325), sage/amber/slate semantic node badges, light Prism syntax highlighting, Plus Jakarta Sans typography, friendly empty state, and instant copy feedback.

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Refreshed UI design tokens, minimap palette, light code viewer, and interactive feedback across all components.
- **Files Modified/Created**:
  - `css/style.css`
  - `index.html`
  - `js/canvas.js`
  - `js/cli-wizard.js`
  - `js/app.js`
  - `assets/prism-light.min.css`

---
## [STAGE-002] v1.1.0 — Automated Documentation Engine & Dynamic Architecture Sync
*Recorded: 2026-10-20 23:00:00 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Eliminate documentation drift between the physical codebase and architectural specifications as the product evolves rapidly.
- **User Story**: As an engineering team and system architect, we require all architecture diagrams, data schemas, and technical process flows to automatically reflect only the latest active code, while maintaining an immutable reverse-chronological history of requirements and design decisions with zero manual upkeep.

### 2. Development Implementation Summary
- **Dynamic Living Architecture (`/docs/architecture/` & `/docs/flows/`)**: Created self-updating technical specifications:
  - `docs/architecture/SYSTEM_ARCHITECTURE.md`: Active subsystem inventory, component dependency matrix, and zero-drift pruning policy.
  - `docs/architecture/DATA_SCHEMAS.md`: Active TypeScript/JSON schemas for nodes and connection topologies.
  - `docs/flows/WORKFLOW_ORCHESTRATION_FLOW.md`: Interactive visual-to-code compiler flow and headless CLI export sequence.
  - `docs/flows/AGENT_EXECUTION_FLOW.md`: Runtime lifecycles for Sequential and Hierarchical CrewAI workflows.
- **Reverse-Chronological Changelog Pipeline**: Built `docs/CHANGELOG_REQUIREMENTS.md` backed by `docs/requirements/SPEC_REGISTRY.json`.
- **Automation Engine (`scripts/doc_pipeline.py`)**: Developed an automated cross-platform Python CLI pipeline capable of:
  - Validating documentation synchronization.
  - Prepending new change records without disturbing historical entries.
  - Synchronizing codebase module lists and verifying active components.
- **CI/CD & Git Automation**: Implemented `.github/workflows/docs-automation.yml` and `.githooks/pre-commit` to automatically verify, sync, and commit documentation on code changes.

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Established `/docs/` as a live mirror of codebase truth rather than static manual text. Added validation gate in CI pipeline.
- **Process Flow Impact**: Commits and pull requests automatically trigger the documentation sync pass, ensuring that whenever a feature is modified or removed, documentation is updated immediately.
- **Files Modified/Created**:
  - `docs/architecture/SYSTEM_ARCHITECTURE.md`
  - `docs/architecture/DATA_SCHEMAS.md`
  - `docs/flows/WORKFLOW_ORCHESTRATION_FLOW.md`
  - `docs/flows/AGENT_EXECUTION_FLOW.md`
  - `docs/requirements/SPEC_REGISTRY.json`
  - `docs/CHANGELOG_REQUIREMENTS.md`
  - `scripts/doc_pipeline.py`
  - `.github/workflows/docs-automation.yml`
  - `.githooks/pre-commit`

---

## [STAGE-001] v1.0.0 — Visual CrewAI Agent & Workflow Builder Release
*Recorded: 2026-10-20 22:30:00 UTC* • **Status: COMPLETED**

### 1. Business Requirement & User Story
- **Business Need**: Enable technical and non-technical developers to visually orchestrate multi-agent CrewAI systems without writing verbose YAML and Python configuration boilerplate.
- **User Story**: As an AI engineer or project lead, I want a modern visual canvas where I can drag agents, tasks, and tools, configure parameters safely, test flows in a dry-run terminal simulator, and export production-ready CrewAI repositories or single-file scripts instantly.

### 2. Development Implementation Summary
- **Interactive Visual Canvas**: Developed infinite pan/zoom canvas (`js/canvas.js`) with 20px magnetic grid snapping, dynamic SVG cubic bezier connectors, and real-time interactive minimap.
- **Node Property Inspector**: Built slide-over inspector (`js/inspector.js`) supporting OpenAI, Anthropic, Google Gemini, Groq, and 100% offline local Ollama models with temperature/iteration sliders and delegation toggles.
- **Real-Time Dual Code Generator**: Implemented live compiler (`js/generator.js`) outputting native CrewAI YAMLs (`config/agents.yaml`, `config/tasks.yaml`, `crew.py`, `main.py`), standalone runner (`crew_runner.py`), `.env` key detector, and `requirements.txt`.
- **Turnkey Project Packaging**: Built client-side ZIP packaging engine (`js/exporter.js`) via JSZip for 1-click full repository export.
- **CLI & Simulator Suite**: Developed terminal assistant (`js/cli-wizard.js`) with dry-run execution sandbox and a headless command-line tool (`cli.py`).
- **Local Dev Server**: Implemented UTF-8 compatible Python server (`server.py`).

### 3. Impact on System Architecture & Process Flows
- **Architectural Impact**: Created the initial client-side reactive graph architecture, module schemas, tool registry, and multi-file code compiler.
- **Process Flow Impact**: Established the complete visual workflow pipeline: Canvas User Action ➔ Graph State ➔ Live Dual Compiler ➔ Single-File or ZIP Export ➔ CLI Execution.
- **Files Created**:
  - `index.html`
  - `css/style.css`
  - `js/canvas.js`
  - `js/nodes.js`
  - `js/inspector.js`
  - `js/generator.js`
  - `js/templates.js`
  - `js/cli-wizard.js`
  - `js/exporter.js`
  - `js/app.js`
  - `server.py`
  - `cli.py`
  - `README.md`

<!-- AUTO_CHANGELOG_END -->
