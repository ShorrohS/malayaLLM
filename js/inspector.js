/**
 * Visual CrewAI Agent & Workflow Builder
 * Node Property Inspector / Sidebar
 */

import { LLM_MODELS, TOOL_DEFINITIONS, NODE_TYPES } from './nodes.js';

export class Inspector {
  constructor(sidebarEl, onUpdateNode) {
    this.sidebar = sidebarEl;
    this.onUpdateNode = onUpdateNode;
    this.currentNode = null;
    this.allNodes = [];

    this.headerEl = this.sidebar.querySelector('.inspector-header');
    this.bodyEl = this.sidebar.querySelector('.inspector-body');
    this.closeBtn = this.sidebar.querySelector('.close-inspector-btn');

    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.close());
    }
  }

  setAllNodes(nodes) {
    this.allNodes = nodes;
  }

  open(node, allNodes = []) {
    this.currentNode = node;
    this.allNodes = allNodes;
    this.sidebar.classList.remove('collapsed');
    this.render();
  }

  close() {
    this.sidebar.classList.add('collapsed');
    this.currentNode = null;
  }

  render() {
    if (!this.currentNode) {
      this.bodyEl.innerHTML = `
        <div style="text-align: center; color: var(--text-dim); margin-top: 60px;">
          <p style="font-size: 2rem; margin-bottom: 8px;">👈</p>
          <p style="font-size: 0.9rem; font-weight: 500;">Select a node on canvas</p>
          <p style="font-size: 0.75rem; margin-top: 4px;">Click any Agent, Task, Tool, or Crew to configure its parameters.</p>
        </div>
      `;
      return;
    }

    const n = this.currentNode;
    let html = '';

    if (n.type === NODE_TYPES.AGENT) {
      html = this.renderAgentInspector(n);
    } else if (n.type === NODE_TYPES.TASK) {
      html = this.renderTaskInspector(n);
    } else if (n.type === NODE_TYPES.TOOL) {
      html = this.renderToolInspector(n);
    } else if (n.type === NODE_TYPES.CREW) {
      html = this.renderCrewInspector(n);
    }

    this.bodyEl.innerHTML = html;
    this.attachEventListeners();
  }

  renderAgentInspector(agent) {
    // Group models by provider
    let modelOptions = '';
    for (const [provider, models] of Object.entries(LLM_MODELS)) {
      modelOptions += `<optgroup label="${provider}">`;
      models.forEach(m => {
        const selected = m.id === agent.model_name ? 'selected' : '';
        modelOptions += `<option value="${m.id}" data-provider="${provider}" ${selected}>${m.name}</option>`;
      });
      modelOptions += `</optgroup>`;
    }

    return `
      <div class="form-group">
        <label class="form-label">Agent Variable Name <span class="form-label-help">Used in Python code</span></label>
        <input type="text" class="form-input" id="prop_name" value="${agent.name || ''}" placeholder="e.g. Senior_Researcher">
      </div>

      <div class="form-group">
        <label class="form-label">Role <span class="form-label-help">Core agent title</span></label>
        <input type="text" class="form-input" id="prop_role" value="${agent.role || ''}" placeholder="e.g. Senior Security Auditor">
      </div>

      <div class="form-group">
        <label class="form-label">Goal <span class="form-label-help">What the agent strives to achieve</span></label>
        <textarea class="form-textarea" id="prop_goal" rows="3">${agent.goal || ''}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label">Backstory <span class="form-label-help">Persona, style, and tone prompt</span></label>
        <textarea class="form-textarea" id="prop_backstory" rows="4">${agent.backstory || ''}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label">LLM Provider & Model</label>
        <select class="form-select" id="prop_model_name">
          ${modelOptions}
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">
          <span>Temperature</span>
          <span class="slider-val" id="temp_display">${agent.temperature ?? 0.7}</span>
        </label>
        <div class="slider-container">
          <input type="range" class="form-slider" id="prop_temperature" min="0" max="1" step="0.05" value="${agent.temperature ?? 0.7}">
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">
          <span>Max Iterations</span>
          <span class="slider-val" id="iter_display">${agent.max_iter || 25}</span>
        </label>
        <div class="slider-container">
          <input type="range" class="form-slider" id="prop_max_iter" min="5" max="50" step="1" value="${agent.max_iter || 25}">
        </div>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Allow Delegation</span>
          <span class="toggle-desc">Delegate subtasks to other agents</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_allow_delegation" ${agent.allow_delegation ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Agent Memory</span>
          <span class="toggle-desc">Short-term & entity vector storage</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_memory" ${agent.memory ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Verbose Logging</span>
          <span class="toggle-desc">Stream execution thoughts to console</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_verbose" ${agent.verbose ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>
    `;
  }

  renderTaskInspector(task) {
    const agents = this.allNodes.filter(n => n.type === NODE_TYPES.AGENT);
    let agentOptions = `<option value="">-- Auto / None --</option>`;
    agents.forEach(a => {
      const selected = a.id === task.agent_id ? 'selected' : '';
      agentOptions += `<option value="${a.id}" ${selected}>${a.role || a.name}</option>`;
    });

    return `
      <div class="form-group">
        <label class="form-label">Task Variable Name</label>
        <input type="text" class="form-input" id="prop_name" value="${task.name || ''}" placeholder="e.g. Conduct_Research_Task">
      </div>

      <div class="form-group">
        <label class="form-label">Task Title / Display</label>
        <input type="text" class="form-input" id="prop_title" value="${task.title || ''}" placeholder="e.g. Conduct Deep Analysis">
      </div>

      <div class="form-group">
        <label class="form-label">Assigned Agent</label>
        <select class="form-select" id="prop_agent_id">
          ${agentOptions}
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Task Description <span class="form-label-help">Detailed prompt instructions</span></label>
        <textarea class="form-textarea" id="prop_description" rows="4">${task.description || ''}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label">Expected Output <span class="form-label-help">Formatting & criteria expectations</span></label>
        <textarea class="form-textarea" id="prop_expected_output" rows="3">${task.expected_output || ''}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label">Output File Path <span class="form-label-help">Optional disk export</span></label>
        <input type="text" class="form-input" id="prop_output_file" value="${task.output_file || ''}" placeholder="e.g. reports/analysis.md">
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Async Execution</span>
          <span class="toggle-desc">Run concurrently alongside other tasks</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_async_execution" ${task.async_execution ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Human Input Approval</span>
          <span class="toggle-desc">Pause execution for user feedback</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_human_input" ${task.human_input ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>
    `;
  }

  renderToolInspector(tool) {
    let toolTypeOptions = '';
    for (const [key, def] of Object.entries(TOOL_DEFINITIONS)) {
      const selected = key === tool.tool_type ? 'selected' : '';
      toolTypeOptions += `<option value="${key}" ${selected}>${def.name}</option>`;
    }

    const isCustom = tool.tool_type === 'CustomPythonTool';
    const def = TOOL_DEFINITIONS[tool.tool_type] || {};

    return `
      <div class="form-group">
        <label class="form-label">Tool Preset Type</label>
        <select class="form-select" id="prop_tool_type">
          ${toolTypeOptions}
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Display Name</label>
        <input type="text" class="form-input" id="prop_name" value="${tool.name || ''}">
      </div>

      <div class="form-group">
        <label class="form-label">Required API Key Environment Variable</label>
        <input type="text" class="form-input" id="prop_api_key_env" value="${tool.api_key_env || def.reqKey || ''}" placeholder="e.g. SERPER_API_KEY">
      </div>

      <div style="font-size: 0.78rem; color: var(--text-dim); background: rgba(255,255,255,0.03); padding: 8px 10px; border-radius: var(--radius-sm);">
        ${def.desc || 'Reusable tool attached to agents to grant specialized web, file, or search abilities.'}
      </div>

      ${isCustom ? `
        <div class="form-group">
          <label class="form-label">Custom Python Tool Code (@tool)</label>
          <textarea class="form-textarea" id="prop_custom_code" rows="7" style="font-family: var(--font-mono); font-size: 0.75rem;">${tool.custom_code || ''}</textarea>
        </div>
      ` : ''}
    `;
  }

  renderCrewInspector(crew) {
    return `
      <div class="form-group">
        <label class="form-label">Crew Project Name</label>
        <input type="text" class="form-input" id="prop_name" value="${crew.name || ''}" placeholder="e.g. AutonomousExecutiveCrew">
      </div>

      <div class="form-group">
        <label class="form-label">Process Execution Type</label>
        <select class="form-select" id="prop_process">
          <option value="sequential" ${crew.process === 'sequential' ? 'selected' : ''}>Sequential (Step-by-step pipeline)</option>
          <option value="hierarchical" ${crew.process === 'hierarchical' ? 'selected' : ''}>Hierarchical (Manager delegates to team)</option>
        </select>
      </div>

      <div class="form-group" id="group_manager_llm" style="${crew.process === 'hierarchical' ? '' : 'display: none;'}">
        <label class="form-label">Manager LLM <span class="form-label-help">Required for Hierarchical</span></label>
        <input type="text" class="form-input" id="prop_manager_llm" value="${crew.manager_llm || 'gpt-4o'}" placeholder="e.g. gpt-4o">
      </div>

      <div class="form-group">
        <label class="form-label">
          <span>Max Requests Per Minute (RPM)</span>
          <span class="slider-val" id="rpm_display">${crew.max_rpm || 100}</span>
        </label>
        <div class="slider-container">
          <input type="range" class="form-slider" id="prop_max_rpm" min="10" max="300" step="10" value="${crew.max_rpm || 100}">
        </div>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Crew Memory</span>
          <span class="toggle-desc">Enable shared short & long-term memory</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_memory" ${crew.memory ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-title">Tool Result Cache</span>
          <span class="toggle-desc">Cache tool outputs to save cost & time</span>
        </div>
        <label class="switch">
          <input type="checkbox" id="prop_cache" ${crew.cache ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="form-group">
        <label class="form-label">Console Verbosity Level</label>
        <select class="form-select" id="prop_verbose">
          <option value="1" ${crew.verbose == 1 ? 'selected' : ''}>1 - Standard info</option>
          <option value="2" ${crew.verbose == 2 ? 'selected' : ''}>2 - Detailed reasoning & tool inputs</option>
        </select>
      </div>
    `;
  }

  attachEventListeners() {
    if (!this.currentNode) return;
    const inputs = this.bodyEl.querySelectorAll('input, select, textarea');

    inputs.forEach(input => {
      const fieldId = input.id.replace('prop_', '');

      // Special slider label updaters
      if (input.id === 'prop_temperature') {
        input.addEventListener('input', () => {
          const display = document.getElementById('temp_display');
          if (display) display.textContent = input.value;
        });
      }
      if (input.id === 'prop_max_iter') {
        input.addEventListener('input', () => {
          const display = document.getElementById('iter_display');
          if (display) display.textContent = input.value;
        });
      }
      if (input.id === 'prop_max_rpm') {
        input.addEventListener('input', () => {
          const display = document.getElementById('rpm_display');
          if (display) display.textContent = input.value;
        });
      }

      // Hierarchy toggle show/hide manager_llm
      if (input.id === 'prop_process') {
        input.addEventListener('change', () => {
          const mgrGroup = document.getElementById('group_manager_llm');
          if (mgrGroup) {
            mgrGroup.style.display = input.value === 'hierarchical' ? '' : 'none';
          }
        });
      }

      // Tool type change updates name and api_key_env
      if (input.id === 'prop_tool_type') {
        input.addEventListener('change', () => {
          const def = TOOL_DEFINITIONS[input.value];
          if (def) {
            const nameInp = document.getElementById('prop_name');
            const keyInp = document.getElementById('prop_api_key_env');
            if (nameInp) nameInp.value = def.name;
            if (keyInp) keyInp.value = def.reqKey || '';
            this.handlePropChange('tool_type', input.value);
            this.handlePropChange('name', def.name);
            this.handlePropChange('api_key_env', def.reqKey || null);
            this.render();
          }
        });
      }

      const handleChange = () => {
        let value = input.type === 'checkbox' ? input.checked : input.value;
        if (input.type === 'range') value = parseFloat(value);
        if (fieldId === 'verbose') value = parseInt(value, 10);
        this.handlePropChange(fieldId, value);
      };

      input.addEventListener('change', handleChange);
      if (input.tagName === 'INPUT' && input.type === 'text') {
        input.addEventListener('input', handleChange);
      }
    });
  }

  handlePropChange(field, value) {
    if (!this.currentNode) return;
    const updates = { [field]: value };
    this.onUpdateNode(this.currentNode.id, updates);
  }
}
