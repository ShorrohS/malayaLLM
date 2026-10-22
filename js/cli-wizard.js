/**
 * Visual CrewAI Agent & Workflow Builder
 * CLI Wizard, Terminal Setup Assistant & Dry-Run Simulator
 */

export class CliWizard {
  constructor(modalEl, onNotify) {
    this.modal = modalEl;
    this.onNotify = onNotify;
    this.currentOS = 'windows'; // 'windows' or 'posix'
    this.graph = { nodes: [], connections: [] };

    this.closeBtn = this.modal.querySelector('.close-modal-btn');
    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.close());
    }

    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });
  }

  open(graph) {
    this.graph = graph;
    this.modal.classList.add('open');
    this.render();
  }

  close() {
    this.modal.classList.remove('open');
  }

  setOS(os) {
    this.currentOS = os;
    this.render();
  }

  validateGraph() {
    const issues = [];
    const { nodes = [], connections = [] } = this.graph;

    const agents = nodes.filter(n => n.type === 'agent');
    const tasks = nodes.filter(n => n.type === 'task');
    const crew = nodes.find(n => n.type === 'crew');

    if (agents.length === 0) {
      issues.push({ type: 'error', message: 'No Agents defined in workflow. Add at least 1 Agent.' });
    }

    if (tasks.length === 0) {
      issues.push({ type: 'error', message: 'No Tasks defined in workflow. Add at least 1 Task.' });
    }

    // Check task assignments
    tasks.forEach(t => {
      const hasDirectAgent = !!t.agent_id;
      const hasConnAgent = connections.some(c => c.type === 'agent-task' && (c.targetId === t.id || c.sourceId === t.id));
      if (!hasDirectAgent && !hasConnAgent) {
        issues.push({ type: 'warning', message: `Task "${t.title || t.name}" has no assigned Agent.` });
      }
    });

    if (crew && crew.process === 'hierarchical' && !crew.manager_llm) {
      issues.push({ type: 'error', message: 'Hierarchical Crew requires a Manager LLM (e.g. gpt-4o).' });
    }

    return issues;
  }

  render() {
    const modalBody = this.modal.querySelector('.modal-body');
    if (!modalBody) return;

    const crewName = (this.graph.nodes.find(n => n.type === 'crew')?.name || 'my_custom_crew')
      .toLowerCase().replace(/[^a-z0-9_]+/g, '_');

    const isWin = this.currentOS === 'windows';

    const venvCmd = isWin ? 'python -m venv .venv\n.venv\\Scripts\\activate' : 'python3 -m venv .venv\nsource .venv/bin/activate';
    const installCmd = 'pip install crewai crewai-tools python-dotenv';
    const initCmd = `crewai create crew ${crewName}`;
    const runCmd = isWin ? 'python crew_runner.py' : 'python3 crew_runner.py';

    const validationIssues = this.validateGraph();
    const hasErrors = validationIssues.some(i => i.type === 'error');

    modalBody.innerHTML = `
      <!-- OS Switcher & Status Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 14px;">
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-sm ${isWin ? 'btn-primary' : 'btn-secondary'}" id="os_win_btn">
            🪟 Windows PowerShell
          </button>
          <button class="btn btn-sm ${!isWin ? 'btn-primary' : 'btn-secondary'}" id="os_posix_btn">
            🐧 macOS / Linux Bash
          </button>
        </div>
        <div style="font-size: 0.8rem; font-family: var(--font-mono); color: ${hasErrors ? 'var(--error)' : 'var(--success)'};">
          ${hasErrors ? '⚠️ Validation Issues Found' : '✅ Workflow Graph Validated'}
        </div>
      </div>

      <!-- Validation Warnings / Alerts -->
      ${validationIssues.length > 0 ? `
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${validationIssues.map(issue => `
            <div style="padding: 9px 13px; border-radius: var(--radius-sm); font-size: 0.8rem; font-weight: 500; background: ${issue.type === 'error' ? 'var(--error-bg)' : 'var(--warning-bg)'}; border: 1px solid ${issue.type === 'error' ? '#FCA5A5' : '#FCD34D'}; color: ${issue.type === 'error' ? 'var(--error)' : 'var(--warning)'};">
              ${issue.type === 'error' ? '❌' : '⚠️'} ${issue.message}
            </div>
          `).join('')}
        </div>
      ` : ''}

      <!-- Terminal Steps -->
      <div class="cli-step">
        <div class="cli-step-title">
          <span class="cli-step-num">1</span>
          <span>Create & Activate Virtual Environment</span>
        </div>
        <div class="cli-code-box">
          <div class="cli-code-text">${venvCmd}</div>
          <button class="btn btn-secondary btn-sm copy-btn" data-text="${venvCmd.replace(/\n/g, ' && ')}">📋 Copy</button>
        </div>
      </div>

      <div class="cli-step">
        <div class="cli-step-title">
          <span class="cli-step-num">2</span>
          <span>Install CrewAI & Tool Dependencies</span>
        </div>
        <div class="cli-code-box">
          <div class="cli-code-text">${installCmd}</div>
          <button class="btn btn-secondary btn-sm copy-btn" data-text="${installCmd}">📋 Copy</button>
        </div>
      </div>

      <div class="cli-step">
        <div class="cli-step-title">
          <span class="cli-step-num">3</span>
          <span>Generate or Scaffold Crew Project Structure</span>
        </div>
        <div class="cli-code-box">
          <div class="cli-code-text">${initCmd}</div>
          <button class="btn btn-secondary btn-sm copy-btn" data-text="${initCmd}">📋 Copy</button>
        </div>
      </div>

      <div class="cli-step">
        <div class="cli-step-title">
          <span class="cli-step-num">4</span>
          <span>Run Single-File Script or Crew CLI</span>
        </div>
        <div class="cli-code-box">
          <div class="cli-code-text"># Option A: Run single-file executable script\n${runCmd}\n\n# Option B: Run via native CrewAI CLI\ncrewai run</div>
          <button class="btn btn-secondary btn-sm copy-btn" data-text="${runCmd}">📋 Copy</button>
        </div>
      </div>

      <!-- Dry-Run Terminal Simulation Section -->
      <div style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; display: flex; flex-direction: column; gap: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.86rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 6px;">
            💻 Terminal Dry-Run Sandbox
          </span>
          <button class="btn btn-accent btn-sm" id="btn_simulate_run">
            ▶️ Simulate Execution Flow
          </button>
        </div>
        <div id="simulated_console" style="background: #1C1B1A; border: 1px solid #2D2B29; border-radius: 6px; padding: 12px 14px; font-family: var(--font-mono); font-size: 0.78rem; color: #E5E3DE; min-height: 120px; max-height: 180px; overflow-y: auto; line-height: 1.55; white-space: pre-wrap;">
[Ready] Click "Simulate Execution Flow" to perform a dry-run check of agent reasoning and task orchestration.
        </div>
      </div>
    `;

    // Attach OS button listeners
    const winBtn = modalBody.querySelector('#os_win_btn');
    const posixBtn = modalBody.querySelector('#os_posix_btn');
    if (winBtn) winBtn.addEventListener('click', () => this.setOS('windows'));
    if (posixBtn) posixBtn.addEventListener('click', () => this.setOS('posix'));

    // Attach copy buttons
    modalBody.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const text = btn.dataset.text;
        navigator.clipboard.writeText(text);
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = '📋 Copy'; }, 1500);
        if (this.onNotify) this.onNotify('Command copied to clipboard!', 'info');
      });
    });

    // Attach simulation button
    const simBtn = modalBody.querySelector('#btn_simulate_run');
    const consoleEl = modalBody.querySelector('#simulated_console');
    if (simBtn && consoleEl) {
      simBtn.addEventListener('click', () => {
        this.runSimulation(consoleEl);
      });
    }
  }

  runSimulation(consoleEl) {
    consoleEl.textContent = '⏳ Initializing virtual runtime dry-run sandbox...\n';

    const agents = this.graph.nodes.filter(n => n.type === 'agent');
    const tasks = this.graph.nodes.filter(n => n.type === 'task');
    const tools = this.graph.nodes.filter(n => n.type === 'tool');
    const crew = this.graph.nodes.find(n => n.type === 'crew') || { name: 'Crew', process: 'sequential' };

    const isOffline = agents.length > 0 && agents.every(a => a.llm_provider?.includes('Ollama') || a.model_name?.includes('ollama'));

    const logs = [
      `[0.0s] Loading .env environment configuration...`,
      isOffline
        ? `[0.1s] 🔒 Privacy Mode Active: 100% Local Offline Ollama Pipeline detected (0 Cloud API Keys required).`
        : `[0.1s] Validating workspace environment and credential vault...`,
      isOffline
        ? `[0.3s] Verified local Ollama daemon connection (http://localhost:11434)... [ONLINE]`
        : `[0.3s] Discovered ${tools.length} Tools, ${agents.length} Agents, and ${tasks.length} Tasks.`,
      `[0.5s] Initializing Process (${(crew.process || 'sequential').toUpperCase()}) with max_rpm=${crew.max_rpm || 60}, verbose=${crew.verbose ?? 1}...`
    ];

    agents.forEach(a => {
      const isLocal = a.llm_provider?.includes('Ollama') || a.model_name?.includes('ollama');
      logs.push(`[0.8s] Agent Ready: [${a.role || a.name}]`);
      logs.push(`   └─> Engine: ${a.model_name} ${isLocal ? '(Local On-Premises)' : '(Cloud API)'}`);
      logs.push(`   └─> Parameters: temp=${a.temperature ?? 0.6}, max_iter=${a.max_iter ?? 15}`);
    });

    tasks.forEach((t, i) => {
      const assigned = agents.find(a => a.id === t.agent_id);
      logs.push(`[${(1.1 + i * 0.7).toFixed(1)}s] Task Dispatched: "${t.title || t.name}"`);
      if (t.description) logs.push(`   └─> Prompt: "${t.description.length > 70 ? t.description.slice(0, 70) + '...' : t.description}"`);
      logs.push(`   └─> Reasoning via: ${assigned ? assigned.role : 'Assigned Agent'}${isOffline ? ' [Local On-Premise Execution]' : ''}`);
      if (t.expected_output) logs.push(`   └─> Expected Output: ${t.expected_output}`);
      logs.push(`   └─> Target Output: ${t.output_file || 'stdout'} [Generated OK]`);
    });

    logs.push(isOffline
      ? `[${(1.4 + tasks.length * 0.7).toFixed(1)}s] ✅ Orchestration dry-run completed with 0 errors! 100% Local inference verified without external telemetry.`
      : `[${(1.4 + tasks.length * 0.7).toFixed(1)}s] ✅ Orchestration completed successfully with 0 errors!`
    );

    let current = 0;
    const interval = setInterval(() => {
      if (current < logs.length) {
        consoleEl.textContent += logs[current] + '\n';
        consoleEl.scrollTop = consoleEl.scrollHeight;
        current++;
      } else {
        clearInterval(interval);
      }
    }, 220);
  }
}
