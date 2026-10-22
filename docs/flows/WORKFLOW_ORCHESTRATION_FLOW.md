# Workflow Orchestration Technical Process Flows

> **Auto-Generated & Synchronized Document**  
> **Source of Truth Policy**: Describes the active runtime and build flows implemented in `js/canvas.js`, `js/generator.js`, and `cli.py`.

---

## 1. Visual Canvas to Code Compilation Flow

This sequence depicts how a user action on the visual canvas instantly translates into compiled CrewAI deliverables across all tabs.

```mermaid
sequenceDiagram
    autonumber
    actor User as Developer / Designer
    participant Palette as Palette Dock
    participant Canvas as Canvas Engine (canvas.js)
    participant Inspector as Inspector Drawer (inspector.js)
    participant State as Graph State
    participant Compiler as Generator Engine (generator.js)
    participant Tabs as Code Viewer & Tabs (app.js)

    User->>Palette: Drag or Click Node Component
    Palette->>Canvas: Instantiate Default Node (Agent / Task / Tool / Crew)
    Canvas->>State: Append to nodes array & trigger render
    User->>Canvas: Drag connector port (e.g. Tool -> Agent)
    Canvas->>State: Validate & append to connections array
    User->>Inspector: Modify Parameter (e.g. Temperature, Model, Output File)
    Inspector->>State: updateNodeData(nodeId, updates)
    
    State->>Compiler: Trigger generateCrewProject(graph)
    activate Compiler
    Compiler->>Compiler: Parse Agents & Tools mapping
    Compiler->>Compiler: Assign Tasks & Dependency Sequence
    Compiler->>Compiler: Auto-detect required Environment API Keys
    Compiler->>Compiler: Format Native YAMLs (agents.yaml, tasks.yaml)
    Compiler->>Compiler: Render Python Decorators & Single Runner (crew_runner.py)
    Compiler->>Compiler: Construct requirements.txt & .env
    Compiler-->>Tabs: Return Compiled Code Object
    deactivate Compiler

    Tabs->>Tabs: Prism.highlight() active file view
    Tabs->>User: Display updated real-time syntax highlighted code
```

---

## 2. Project Export & Packaging Flow

```mermaid
flowchart TD
    Start([User clicks 'Export ZIP']) --> GatherState[Fetch Current Graph State from Canvas]
    GatherState --> Compile[Run generateCrewProject Graph]
    Compile --> CheckJSZip{Is JSZip Available?}
    
    CheckJSZip -- Yes --> CreateZip[Initialize JSZip Instance]
    CreateZip --> AddConfig[Add config/agents.yaml & config/tasks.yaml]
    AddConfig --> AddSource[Add crew.py, main.py, crew_runner.py]
    AddSource --> AddMeta[Add .env, requirements.txt, README.md, workflow.crewai.json]
    AddMeta --> GenerateBlob[zip.generateAsync as Blob]
    GenerateBlob --> TriggerDownload[Browser Triggers Download of my_crew_project.zip]
    
    CheckJSZip -- No --> Fallback[Fallback: Download standalone crew_runner.py]
    Fallback --> Notify[Notify User via Toast Notification]
    TriggerDownload --> Notify
```

---

## 3. Headless CLI Pipeline Execution Flow

```mermaid
flowchart LR
    CLICommand["python cli.py generate workflow.json --out-dir ./crew"] --> ParseFile[Read & Parse JSON]
    ParseFile --> Validate{validate_workflow}
    Validate -- Errors Found --> Halt[Print Validation Errors & Exit 1]
    Validate -- Clean --> Scaffold[Scaffold Output Directory Structure]
    Scaffold --> WriteYAML[Write config/agents.yaml & config/tasks.yaml]
    WriteYAML --> WriteCode[Write crew_runner.py]
    WriteCode --> WriteConfig[Write .env & requirements.txt]
    WriteConfig --> Done([Project Scaffolded & Ready for 'crewai run'])
```
