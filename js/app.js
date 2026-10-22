/**
 * Visual CrewAI Agent & Workflow Builder
 * Professional Operations Center - Main Application Orchestrator
 */

import { CanvasEngine } from './canvas.js';
import { Inspector } from './inspector.js';
import { CliWizard } from './cli-wizard.js';
import { Exporter } from './exporter.js';
import { generateCrewProject } from './generator.js';
import { WORKFLOW_TEMPLATES } from './templates.js';
import { KeyVault, CLOUD_PROVIDERS } from './key-vault.js';
import { DiagnosticsManager } from './diagnostics.js';
import { DatasetReviewManager } from './dataset-review.js';
import { 
  NODE_TYPES, 
  createDefaultAgent, 
  createDefaultTask, 
  createDefaultTool, 
  createDefaultCrew 
} from './nodes.js';

class App {
  constructor() {
    this.currentTab = 'native'; // 'native' | 'single' | 'env' | 'reqs' | 'cli' | 'diagnostics' | 'dataset_review' | 'colab_bridge'
    this.currentSubFile = 'agents.yaml'; // 'agents.yaml' | 'tasks.yaml' | 'crew.py' | 'main.py'
    this.cachedCode = {};

    this.initDOM();
    this.initComponents();
    this.initPaletteDragAndSearch();
    this.initCodeDrawer();
    this.initKeyVaultModal();
    this.initTopNavActions();
    this.loadInitialWorkflow();
  }

  initDOM() {
    this.containerEl = document.getElementById('canvas_container');
    this.worldEl = document.getElementById('canvas_world');
    this.svgEl = document.getElementById('connections_layer');
    this.minimapCanvas = document.getElementById('minimap_canvas');
    this.inspectorEl = document.getElementById('inspector_sidebar');
    this.cliModalEl = document.getElementById('cli_modal');
    this.vaultModalEl = document.getElementById('vault_modal');
    this.toastContainer = document.getElementById('toast_container');

    // Code & Console drawer DOM
    this.codeDrawer = document.getElementById('code_drawer');
    this.codeViewWrapper = document.getElementById('code_view_wrapper');
    this.codeContentEl = document.getElementById('code_content');
    this.subFileBar = document.getElementById('sub_file_bar');
    this.zoomDisplay = document.getElementById('zoom_display');

    // Header pills & badges
    this.headerStatusBadge = document.getElementById('btn_header_status');
    this.headerStatusText = document.getElementById('header_status_text');
    this.healthPill = document.getElementById('btn_health_pill');
    this.healthPillText = document.getElementById('health_pill_text');
    this.vaultKeyCountBadge = document.getElementById('vault_key_count');
    this.diagWarningBadge = document.getElementById('diag_warning_count');
    this.activeCrewPill = document.getElementById('active_crew_pill');
    this.topPendingBadge = document.getElementById('top_pending_badge');
    this.dockPendingBadge = document.getElementById('dock_pending_badge');

    // Tab panels
    this.cliTabPanel = document.getElementById('cli_tab_panel');
    this.diagnosticsTabPanel = document.getElementById('diagnostics_tab_panel');
    this.datasetReviewPanel = document.getElementById('dataset_review_panel');
    this.colabBridgePanel = document.getElementById('colab_bridge_panel');
  }

  notify(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    this.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  initComponents() {
    // 1. Exporter
    this.exporter = new Exporter((msg, type) => this.notify(msg, type));

    // 2. Key Vault (Cloud Keys & Ollama auto-discovery)
    this.keyVault = new KeyVault({
      onKeysUpdated: (keys) => {
        this.updateVaultPills();
        this.refreshCode();
        this.runDiagnostics();
      },
      onOllamaUpdated: (status) => {
        this.updateOllamaStatusPills(status);
        this.renderVaultModalContent();
        this.runDiagnostics();
      },
      onNotify: (msg, type) => this.notify(msg, type)
    });

    // 3. Diagnostics Engine
    this.diagnostics = new DiagnosticsManager({
      onFixIssue: (action) => this.handleFixIssue(action)
    });

    // 4. CLI Wizard
    this.cliWizard = new CliWizard(this.cliModalEl, (msg, type) => this.notify(msg, type));

    // 5. Inspector
    this.inspector = new Inspector(this.inspectorEl, (nodeId, updates) => {
      this.canvas.updateNodeData(nodeId, updates);
    });

    // 6. Dataset Review Queue (Human-in-the-Loop)
    this.datasetReviewManager = new DatasetReviewManager(this.datasetReviewPanel, {
      onNotify: (msg, type) => this.notify(msg, type),
      onApprovedCountChanged: (pending, approved) => this.updateDatasetBadges(pending, approved)
    });
    // Initial fetch of dataset queue counts
    this.datasetReviewManager.loadDatasets();

    // 6. Interactive Canvas Engine
    this.canvas = new CanvasEngine(
      this.containerEl,
      this.worldEl,
      this.svgEl,
      this.minimapCanvas,
      {
        onSelectNode: (node, openInspector) => {
          if (node) {
            this.inspector.open(node, this.canvas.nodes);
          } else {
            this.inspector.close();
          }
        },
        onGraphChanged: () => {
          this.refreshCode();
          this.runDiagnostics();
          this.saveToStorage();
        },
        onZoomChange: (percent) => {
          if (this.zoomDisplay) this.zoomDisplay.textContent = `${percent}%`;
        },
        onFixIssue: (action) => this.handleFixIssue(action),
        onNotify: (msg, type) => this.notify(msg, type)
      }
    );
  }

  handleFixIssue(action) {
    if (!action) return;
    if (action.type === 'open_vault') {
      this.openKeyVaultModal(action.target);
    } else if (action.type === 'select_node') {
      const node = this.canvas.nodes.find(n => n.id === action.target);
      if (node) {
        this.canvas.selectNode(node.id, true);
        this.notify(`Focused ${node.name || 'node'} in Inspector`, 'info');
      }
    }
  }

  updateVaultPills() {
    const activeCount = this.keyVault.getActiveKeyCount();
    const totalKeys = this.keyVault.getTotalKeyCount();
    if (this.vaultKeyCountBadge) {
      this.vaultKeyCountBadge.textContent = totalKeys > activeCount
        ? `${activeCount}P (${totalKeys}K)`
        : `${activeCount}/${CLOUD_PROVIDERS.length}`;
      this.vaultKeyCountBadge.className = `badge-count ${activeCount > 0 ? 'active' : ''}`;
    }
  }

  updateDatasetBadges(pendingCount, approvedCount) {
    [this.topPendingBadge, this.dockPendingBadge].forEach(b => {
      if (b) {
        b.textContent = pendingCount;
        b.style.display = pendingCount > 0 ? 'inline-flex' : 'none';
      }
    });
  }

  updateOllamaStatusPills(status) {
    const label = status.online 
      ? `Ollama: Connected (${status.models.length} model${status.models.length === 1 ? '' : 's'})` 
      : 'Ollama: Offline';

    if (this.healthPillText) {
      this.healthPillText.textContent = label;
    }

    if (this.healthPill) {
      this.healthPill.className = `health-pulse-pill ${status.online ? 'online' : 'offline'}`;
    }

    const sidebarOllama = document.getElementById('sidebar_ollama_status');
    if (sidebarOllama) {
      sidebarOllama.className = `ollama-status-indicator ${status.online ? 'online' : 'offline'}`;
      const lbl = sidebarOllama.querySelector('.ollama-status-label');
      if (lbl) lbl.textContent = status.online ? `Ollama: ${status.models.length} Models Active` : 'Ollama: Offline';
    }
  }

  runDiagnostics() {
    const graph = this.canvas.getGraphData();
    const report = this.diagnostics.auditWorkflow(graph, this.keyVault);

    // 1. Update node warning badges and error rings on canvas
    this.canvas.setNodeIssues(report.nodeIssues);

    // 2. Update Header Status Badge
    if (report.status === 'healthy') {
      this.headerStatusBadge.className = 'status-indicator-badge healthy';
      this.headerStatusText.textContent = 'All Systems Operational';
    } else {
      const issueCount = report.warnings.length + report.errors.length;
      this.headerStatusBadge.className = 'status-indicator-badge warning';
      this.headerStatusText.textContent = `${issueCount} Issue${issueCount === 1 ? '' : 's'} Detected`;
    }

    // 3. Update active crew pill
    const crewNode = graph.nodes.find(n => n.type === 'crew');
    if (this.activeCrewPill) {
      this.activeCrewPill.textContent = crewNode ? crewNode.name : 'CrewAI Workflow';
    }

    // 4. Update Diagnostics count badge on header button
    if (this.diagWarningBadge) {
      const issueCount = report.warnings.length + report.errors.length;
      if (issueCount > 0) {
        this.diagWarningBadge.textContent = issueCount;
        this.diagWarningBadge.style.display = 'inline-flex';
      } else {
        this.diagWarningBadge.style.display = 'none';
      }
    }

    // 5. Update Diagnostics Tab Panel in dock if active
    this.renderDiagnosticsTabPanel(report);
  }

  initPaletteDragAndSearch() {
    const paletteItems = document.querySelectorAll('.palette-item');

    paletteItems.forEach(item => {
      item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', item.dataset.type);
        if (item.dataset.toolType) {
          e.dataTransfer.setData('text/tool-type', item.dataset.toolType);
        }
      });
    });

    this.containerEl.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });

    this.containerEl.addEventListener('drop', (e) => {
      e.preventDefault();
      const nodeType = e.dataTransfer.getData('text/plain');
      const toolType = e.dataTransfer.getData('text/tool-type');
      if (!nodeType) return;

      const rect = this.containerEl.getBoundingClientRect();
      const worldX = (e.clientX - rect.left - this.canvas.panX) / this.canvas.scale;
      const worldY = (e.clientY - rect.top - this.canvas.panY) / this.canvas.scale;

      this.createAndAddNode(nodeType, Math.round(worldX / 20) * 20, Math.round(worldY / 20) * 20, toolType);
    });

    // Direct click to add at center
    paletteItems.forEach(item => {
      item.addEventListener('click', () => {
        const type = item.dataset.type;
        const toolType = item.dataset.toolType;
        const rect = this.containerEl.getBoundingClientRect();
        const centerX = (rect.width / 2 - this.canvas.panX) / this.canvas.scale;
        const centerY = (rect.height / 2 - this.canvas.panY) / this.canvas.scale;
        this.createAndAddNode(type, Math.round(centerX / 20) * 20, Math.round(centerY / 20) * 20, toolType);
      });
    });

    // Real-Time Component Search Filtering
    const searchInput = document.getElementById('component_search');
    const clearBtn = document.getElementById('search_clear_btn');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        clearBtn.style.display = query ? 'block' : 'none';

        paletteItems.forEach(item => {
          const text = item.textContent.toLowerCase();
          const matches = !query || text.includes(query);
          item.style.display = matches ? 'flex' : 'none';
        });

        // Hide empty category groups
        document.querySelectorAll('.palette-category-group').forEach(grp => {
          const visibleItems = grp.querySelectorAll('.palette-item:not([style*="display: none"])');
          if (grp.dataset.category !== 'presets') {
            grp.style.display = (visibleItems.length > 0 || !query) ? 'block' : 'none';
          }
        });
      });

      // Clear search
      clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchInput.dispatchEvent(new Event('input'));
        searchInput.focus();
      });

      // Global keyboard shortcut Ctrl+K / Cmd+K
      window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      });
    }

    // Template preset selector
    const tmplSelect = document.getElementById('template_selector');
    if (tmplSelect) {
      tmplSelect.addEventListener('change', (e) => {
        const key = e.target.value;
        if (WORKFLOW_TEMPLATES[key]) {
          this.canvas.loadGraph(WORKFLOW_TEMPLATES[key]);
          this.refreshCode();
          this.runDiagnostics();
          this.notify(`Loaded preset: ${WORKFLOW_TEMPLATES[key].name}`, 'info');
        }
      });
    }
  }

  createAndAddNode(type, x, y, toolType = null) {
    let node = null;
    if (type === NODE_TYPES.AGENT) node = createDefaultAgent(x, y);
    else if (type === NODE_TYPES.TASK) node = createDefaultTask(x, y);
    else if (type === NODE_TYPES.TOOL) node = createDefaultTool(x, y, { tool_type: toolType || 'SerperDevTool' });
    else if (type === NODE_TYPES.CREW) node = createDefaultCrew(x, y);

    if (node) {
      this.canvas.addNode(node);
      this.refreshCode();
      this.runDiagnostics();
      this.notify(`Added new ${type.toUpperCase()} node`, 'info');
    }
  }

  initCodeDrawer() {
    // Dock tab switching
    const tabs = document.querySelectorAll('.code-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.currentTab = tab.dataset.tab;

        // Hide all views first
        this.subFileBar.style.display = 'none';
        this.codeViewWrapper.style.display = 'none';
        this.cliTabPanel.style.display = 'none';
        this.diagnosticsTabPanel.style.display = 'none';
        if (this.datasetReviewPanel) this.datasetReviewPanel.style.display = 'none';
        if (this.colabBridgePanel) this.colabBridgePanel.style.display = 'none';

        if (this.currentTab === 'native') {
          this.subFileBar.style.display = 'flex';
          this.codeViewWrapper.style.display = 'block';
          this.updateCodeDisplay();
        } else if (this.currentTab === 'single' || this.currentTab === 'env' || this.currentTab === 'reqs') {
          this.codeViewWrapper.style.display = 'block';
          this.updateCodeDisplay();
        } else if (this.currentTab === 'cli') {
          this.cliTabPanel.style.display = 'block';
          this.renderCliTabPanel();
        } else if (this.currentTab === 'diagnostics') {
          this.diagnosticsTabPanel.style.display = 'block';
          this.renderDiagnosticsTabPanel();
        } else if (this.currentTab === 'dataset_review') {
          if (this.datasetReviewPanel) {
            this.datasetReviewPanel.style.display = 'block';
            this.datasetReviewManager.loadDatasets();
          }
        } else if (this.currentTab === 'colab_bridge') {
          if (this.colabBridgePanel) {
            this.colabBridgePanel.style.display = 'block';
            this.renderColabBridgeTabPanel();
          }
        }
      });
    });

    // Sub-file selector pills for native CrewAI project
    const subPills = document.querySelectorAll('.sub-file-pill');
    subPills.forEach(pill => {
      pill.addEventListener('click', () => {
        subPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.currentSubFile = pill.dataset.file;
        this.updateCodeDisplay();
      });
    });

    // Drawer collapse toggle
    const toggleDrawerBtn = document.getElementById('toggle_drawer_btn');
    if (toggleDrawerBtn) {
      toggleDrawerBtn.addEventListener('click', () => {
        this.codeDrawer.classList.toggle('collapsed');
        const isCollapsed = this.codeDrawer.classList.contains('collapsed');
        toggleDrawerBtn.innerHTML = isCollapsed ? '▲ Expand Dock' : '▼ Minimize';
      });
    }

    // Copy current code with instant visual feedback
    const copyCodeBtn = document.getElementById('copy_code_btn');
    if (copyCodeBtn) {
      copyCodeBtn.addEventListener('click', () => {
        const text = this.getCurrentCodeText();
        navigator.clipboard.writeText(text);
        const originalHtml = copyCodeBtn.innerHTML;
        copyCodeBtn.innerHTML = '✓ Copied!';
        copyCodeBtn.style.color = 'var(--success)';
        copyCodeBtn.style.fontWeight = '600';
        setTimeout(() => {
          copyCodeBtn.innerHTML = originalHtml;
          copyCodeBtn.style.color = '';
          copyCodeBtn.style.fontWeight = '';
        }, 1600);
        this.notify('Current file copied to clipboard!', 'success');
      });
    }

    // Download current file with instant visual feedback
    const downloadFileBtn = document.getElementById('download_file_btn');
    if (downloadFileBtn) {
      downloadFileBtn.addEventListener('click', () => {
        const text = this.getCurrentCodeText();
        const filename = this.getCurrentFileName();
        this.exporter.downloadString(filename, text);
        const originalHtml = downloadFileBtn.innerHTML;
        downloadFileBtn.innerHTML = '✓ Downloaded!';
        downloadFileBtn.style.color = 'var(--accent-terracotta)';
        downloadFileBtn.style.fontWeight = '600';
        setTimeout(() => {
          downloadFileBtn.innerHTML = originalHtml;
          downloadFileBtn.style.color = '';
          downloadFileBtn.style.fontWeight = '';
        }, 1600);
        this.notify(`Downloaded ${filename}`, 'success');
      });
    }
  }

  initKeyVaultModal() {
    const closeBtn = this.vaultModalEl.querySelector('.close-vault-btn');
    if (closeBtn) closeBtn.addEventListener('click', () => this.closeKeyVaultModal());

    this.vaultModalEl.addEventListener('click', (e) => {
      if (e.target === this.vaultModalEl) this.closeKeyVaultModal();
    });

    // Scan Ollama button
    const scanBtn = document.getElementById('btn_scan_ollama');
    if (scanBtn) {
      scanBtn.addEventListener('click', async () => {
        scanBtn.innerHTML = '⏳ Scanning...';
        await this.keyVault.autoFetchOllamaModels();
        scanBtn.innerHTML = '🔄 Scan / Re-check Models';
        this.notify('Local Ollama models refreshed!', 'info');
      });
    }

    // Save Vault button
    const saveBtn = document.getElementById('btn_save_vault');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        const inputs = this.vaultModalEl.querySelectorAll('.key-vault-input');
        const newKeys = {};
        inputs.forEach(inp => {
          newKeys[inp.dataset.envKey] = inp.value.trim();
        });
        this.keyVault.saveKeys(newKeys);
        this.closeKeyVaultModal();
        this.notify('API Keys saved and synced to .env!', 'success');
      });
    }

    // Clear Keys button
    const clearBtn = document.getElementById('btn_clear_keys');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (confirm('Clear all stored cloud API keys from this browser?')) {
          const emptyKeys = {};
          CLOUD_PROVIDERS.forEach(p => emptyKeys[p.envKey] = '');
          this.keyVault.saveKeys(emptyKeys);
          this.renderVaultModalContent();
          this.notify('API keys cleared', 'info');
        }
      });
    }
  }

  openKeyVaultModal(highlightEnvKey = null) {
    this.renderVaultModalContent(highlightEnvKey);
    this.vaultModalEl.classList.add('open');
  }

  closeKeyVaultModal() {
    this.vaultModalEl.classList.remove('open');
  }

  renderVaultModalContent(highlightEnvKey = null) {
    // 1. Ollama status and models chips
    const ollama = this.keyVault.ollamaStatus;
    const badge = document.getElementById('vault_ollama_badge');
    const badgeText = document.getElementById('vault_ollama_status_text');
    const modelsList = document.getElementById('discovered_models_list');

    if (badge && badgeText) {
      badge.className = `ollama-live-badge ${ollama.online ? 'online' : 'offline'}`;
      badgeText.textContent = ollama.online 
        ? `Running (${ollama.models.length} model${ollama.models.length === 1 ? '' : 's'})` 
        : 'Daemon Offline / Unreachable';
    }

    if (modelsList) {
      if (ollama.online && ollama.models.length > 0) {
        modelsList.innerHTML = ollama.models.map(m => {
          const sizeGB = (m.size / (1024 * 1024 * 1024)).toFixed(1);
          return `
            <div class="discovered-model-chip" title="Modified: ${m.modified_at}">
              <span class="model-chip-name">🦙 ${m.name}</span>
              <span class="model-chip-size">${sizeGB} GB</span>
            </div>
          `;
        }).join('');
      } else {
        modelsList.innerHTML = `
          <div class="ollama-empty-notice">
            ${ollama.online ? 'No models downloaded yet. Run <code>ollama pull llama3.2</code> in your terminal.' : 'Start the Ollama daemon via <code>ollama serve</code> to unlock 100% offline local AI.'}
          </div>
        `;
      }
    }

    // 2. Cloud API Keys Grid
    const keysGrid = document.getElementById('cloud_keys_grid');
    if (keysGrid) {
      keysGrid.innerHTML = CLOUD_PROVIDERS.map(p => {
        const currentVal = this.keyVault.getKey(p.envKey);
        const keyList = this.keyVault.getKeyList(p.envKey);
        const isValid = p.validate(currentVal);
        const isHighlighted = highlightEnvKey === p.envKey;

        let statusBadge = '<span class="key-status missing">Missing</span>';
        if (keyList.length > 1) {
          const allValid = keyList.every(k => p.validate(k));
          statusBadge = allValid
            ? `<span class="key-status valid">🟢 ${keyList.length} Keys (Rotator)</span>`
            : `<span class="key-status invalid">🔴 ${keyList.length} Keys (Some Invalid)</span>`;
        } else if (currentVal && isValid) {
          statusBadge = '<span class="key-status valid">🟢 Valid Format</span>';
        } else if (currentVal && !isValid) {
          statusBadge = '<span class="key-status invalid">🔴 Incomplete</span>';
        }

        return `
          <div class="key-vault-card ${isHighlighted ? 'highlighted' : ''}">
            <div class="key-card-header">
              <div class="key-provider-info">
                <span class="provider-icon">${p.icon}</span>
                <span class="provider-name">${p.name}</span>
                <code class="env-code">${p.envKey}</code>
              </div>
              <div class="key-status-wrapper" id="status_${p.envKey}">
                ${statusBadge}
              </div>
            </div>
            <div class="key-input-container">
              <input type="password" 
                class="form-input key-vault-input" 
                id="input_${p.envKey}" 
                data-env-key="${p.envKey}" 
                value="${currentVal}" 
                placeholder="${p.placeholder}">
              <button class="key-toggle-mask" type="button" title="Toggle Show/Hide Key">👁️</button>
            </div>
          </div>
        `;
      }).join('');

      // Attach password visibility toggles & live format listeners
      keysGrid.querySelectorAll('.key-vault-card').forEach(card => {
        const inp = card.querySelector('.key-vault-input');
        const toggleBtn = card.querySelector('.key-toggle-mask');
        const envKey = inp.dataset.envKey;
        const provider = CLOUD_PROVIDERS.find(p => p.envKey === envKey);

        toggleBtn.addEventListener('click', () => {
          inp.type = inp.type === 'password' ? 'text' : 'password';
          toggleBtn.textContent = inp.type === 'password' ? '👁️' : '🔒';
        });

        inp.addEventListener('input', () => {
          const val = inp.value.trim();
          const statusWrap = card.querySelector('.key-status-wrapper');
          if (!val) {
            statusWrap.innerHTML = '<span class="key-status missing">Missing</span>';
          } else {
            const rawList = val.split(/[,\n]+/).map(k => k.trim()).filter(Boolean);
            if (rawList.length > 1) {
              const allOk = rawList.every(k => provider.validate(k));
              statusWrap.innerHTML = allOk
                ? `<span class="key-status valid">🟢 ${rawList.length} Keys (Rotator)</span>`
                : `<span class="key-status invalid">🔴 ${rawList.length} Keys (Check Format)</span>`;
            } else if (provider.validate(val)) {
              statusWrap.innerHTML = '<span class="key-status valid">🟢 Valid Format</span>';
            } else {
              statusWrap.innerHTML = '<span class="key-status invalid">🔴 Incomplete</span>';
            }
          }
        });
      });

      if (highlightEnvKey) {
        setTimeout(() => {
          const el = document.getElementById(`input_${highlightEnvKey}`);
          if (el) {
            el.focus();
            el.select();
          }
        }, 150);
      }
    }
  }

  renderCliTabPanel() {
    this.cliWizard.graph = this.canvas.getGraphData();
    const isWin = this.cliWizard.currentOS === 'windows';
    const crewName = (this.cliWizard.graph.nodes.find(n => n.type === 'crew')?.name || 'my_crew')
      .toLowerCase().replace(/[^a-z0-9_]+/g, '_');

    const venvCmd = isWin ? 'python -m venv .venv\n.venv\\Scripts\\activate' : 'python3 -m venv .venv\nsource .venv/bin/activate';
    const installCmd = 'pip install crewai crewai-tools python-dotenv';
    const initCmd = `crewai create crew ${crewName}`;
    const runCmd = isWin ? 'python crew_runner.py' : 'python3 crew_runner.py';

    this.cliTabPanel.innerHTML = `
      <div class="dock-inner-content">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-sm ${isWin ? 'btn-primary' : 'btn-secondary'}" id="dock_win_btn">Windows PowerShell</button>
            <button class="btn btn-sm ${!isWin ? 'btn-primary' : 'btn-secondary'}" id="dock_posix_btn">macOS / Linux Bash</button>
          </div>
          <button class="btn btn-accent btn-sm" id="dock_sim_btn">▶️ Simulate Execution Flow</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
          <div class="cli-step">
            <div class="cli-step-title"><span class="cli-step-num">1</span> <span>Environment Setup</span></div>
            <div class="cli-code-box">
              <div class="cli-code-text">${venvCmd}</div>
              <button class="btn btn-secondary btn-sm copy-btn" data-text="${venvCmd.replace(/\n/g, ' && ')}">📋 Copy</button>
            </div>
          </div>
          <div class="cli-step">
            <div class="cli-step-title"><span class="cli-step-num">2</span> <span>Run Crew</span></div>
            <div class="cli-code-box">
              <div class="cli-code-text">${runCmd}</div>
              <button class="btn btn-secondary btn-sm copy-btn" data-text="${runCmd}">📋 Copy</button>
            </div>
          </div>
        </div>

        <div style="background: #1C1B1A; border: 1px solid #2D2B29; border-radius: 6px; padding: 10px 14px; font-family: var(--font-mono); font-size: 0.76rem; color: #E5E3DE; min-height: 85px; max-height: 120px; overflow-y: auto; white-space: pre-wrap;" id="dock_console">
[Ready] Click "Simulate Execution Flow" to perform an in-browser dry run of the crew.
        </div>
      </div>
    `;

    document.getElementById('dock_win_btn')?.addEventListener('click', () => {
      this.cliWizard.setOS('windows');
      this.renderCliTabPanel();
    });
    document.getElementById('dock_posix_btn')?.addEventListener('click', () => {
      this.cliWizard.setOS('posix');
      this.renderCliTabPanel();
    });
    document.getElementById('dock_sim_btn')?.addEventListener('click', () => {
      const consoleEl = document.getElementById('dock_console');
      if (consoleEl) this.cliWizard.runSimulation(consoleEl);
    });

    this.cliTabPanel.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        navigator.clipboard.writeText(btn.dataset.text);
        btn.textContent = '✓ Copied!';
        setTimeout(() => { btn.textContent = '📋 Copy'; }, 1500);
      });
    });
  }

  renderDiagnosticsTabPanel(report = null) {
    if (!report) {
      report = this.diagnostics.auditWorkflow(this.canvas.getGraphData(), this.keyVault);
    }

    const issues = [...report.errors, ...report.warnings];
    const ollama = this.keyVault.ollamaStatus;

    this.diagnosticsTabPanel.innerHTML = `
      <div class="dock-inner-content">
        <!-- Diagnostic Summary Header -->
        <div class="diag-header-row">
          <div class="diag-status-pill ${report.status}">
            <span class="status-dot"></span>
            <span>${report.status === 'healthy' ? 'Topology & Diagnostics: All Clear' : `${issues.length} Issues Detected`}</span>
          </div>

          <div class="diag-meta-pills">
            <span class="diag-meta-pill">Nodes: ${report.totalNodes}</span>
            <span class="diag-meta-pill">Connections: ${report.totalConnections}</span>
            <span class="diag-meta-pill">Ollama: ${ollama.online ? 'Online' : 'Offline'}</span>
            <span class="diag-meta-pill">Cloud Keys: ${this.keyVault.getActiveKeyCount()}/5 Configured</span>
          </div>
        </div>

        <!-- Issues List with Click-to-Fix -->
        ${issues.length > 0 ? `
          <div class="diag-issues-list">
            ${issues.map(iss => `
              <div class="diag-issue-item">
                <div class="diag-issue-msg">
                  <span>⚠️</span>
                  <span>${iss.message}</span>
                </div>
                ${iss.fixAction ? `
                  <button class="btn btn-secondary btn-sm diag-fix-btn" data-type="${iss.fixAction.type}" data-target="${iss.fixAction.target}">
                    ${iss.fixAction.label} &rarr;
                  </button>
                ` : ''}
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="diag-clean-state">
            <span>✅</span>
            <span>No topology errors, unassigned tasks, or missing required provider keys found. Your workflow is production-ready!</span>
          </div>
        `}
      </div>
    `;

    this.diagnosticsTabPanel.querySelectorAll('.diag-fix-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.type;
        const target = btn.dataset.target;
        this.handleFixIssue({ type, target });
      });
    });
  }

  async renderColabBridgeTabPanel() {
    if (!this.colabBridgePanel) return;

    this.colabBridgePanel.innerHTML = `
      <div class="dock-inner-content">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <div>
            <h4 style="margin: 0 0 4px 0; font-size: 0.95rem; font-weight: 700; color: var(--text-heading); display: flex; align-items: center; gap: 8px;">
              <span>🚀</span> Google Colab / Kaggle Training Handoff Bridge
              <span class="badge-count" style="background: rgba(45,106,79,0.12); color: var(--node-agent-accent); font-weight: 600;">QLoRA + Unsloth</span>
            </h4>
            <div style="font-size: 0.76rem; color: var(--text-muted);">
              Automated relay-race checkpoint loop for uninterrupted 12-hour session recovery on free T4/V100 GPUs.
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" id="btn_fetch_colab_approved">
              🔄 Refresh Status
            </button>
            <button class="btn btn-secondary btn-sm" id="btn_download_approved_json">
              📥 Download Approved JSON
            </button>
            <button class="btn btn-primary btn-sm" id="btn_copy_colab_script">
              📋 Copy Colab Python Script
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 320px 1fr; gap: 14px;">
          <!-- Left Column: Specs & Pipeline Instructions -->
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 12px;">
              <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-heading); margin-bottom: 8px;">
                ⚙️ Training Configuration
              </div>
              <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.74rem;">
                <div style="display: flex; justify-content: space-between;">
                  <span style="color: var(--text-muted);">Base Model:</span>
                  <span style="font-family: var(--font-mono); font-weight: 600;">unsloth/llama-3-8b-bnb-4bit</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color: var(--text-muted);">Target Quantization:</span>
                  <span style="font-weight: 600; color: var(--node-agent-accent);">4-bit NormalFloat (NF4)</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color: var(--text-muted);">LoRA Rank / Alpha:</span>
                  <span style="font-family: var(--font-mono);">r=16, alpha=32</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color: var(--text-muted);">Seq Length:</span>
                  <span style="font-family: var(--font-mono);">2048 tokens</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color: var(--text-muted);">Checkpoint Path:</span>
                  <span style="font-family: var(--font-mono); font-size: 0.68rem; color: var(--accent-terracotta);">/content/drive/MyDrive/...</span>
                </div>
              </div>
            </div>

            <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 12px;">
              <div style="font-size: 0.78rem; font-weight: 700; color: var(--text-heading); margin-bottom: 8px;">
                🔄 Relay-Race Checkpoint Loop
              </div>
              <p style="font-size: 0.72rem; color: var(--text-muted); line-height: 1.4; margin: 0 0 8px 0;">
                Google Colab disconnects GPU runs after 12 hours. The script mounts Google Drive and detects the latest checkpoint folder (<code>checkpoint-*</code>). If disconnected, re-running the cell automatically resumes without losing epoch progress.
              </p>
              <div id="colab_approved_count_badge" style="font-size: 0.72rem; padding: 6px 10px; background: rgba(224,86,36,0.08); border-radius: 4px; color: var(--accent-terracotta); font-weight: 600;">
                Checking approved corpus records...
              </div>
            </div>
          </div>

          <!-- Right Column: Code Preview & Fast Actions -->
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.72rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">
                colab_trainer_loader.py (Standalone QLoRA Script)
              </span>
              <span id="colab_copy_status" style="font-size: 0.72rem; color: var(--success); font-weight: 600;"></span>
            </div>
            <pre style="background: #1C1B1A; border: 1px solid #2D2B29; border-radius: 6px; padding: 12px; margin: 0; font-family: var(--font-mono); font-size: 0.72rem; color: #E5E3DE; height: 180px; overflow: auto; line-height: 1.4;" id="colab_script_preview">
Loading Colab training script...
            </pre>
          </div>
        </div>
      </div>
    `;

    // Fetch script from backend /api/training/colab_script
    try {
      const resp = await fetch('/api/training/colab_script');
      if (resp.ok) {
        const data = await resp.json();
        const preview = document.getElementById('colab_script_preview');
        if (preview && data.script) {
          preview.textContent = data.script;
        }
      }
    } catch (e) {
      console.warn('Failed to load colab script:', e);
    }

    // Fetch approved count
    try {
      const resp = await fetch('/api/dataset/approved');
      if (resp.ok) {
        const data = await resp.json();
        const badge = document.getElementById('colab_approved_count_badge');
        if (badge) {
          const totalRecords = (data.approved_batches || []).reduce((acc, b) => acc + (b.total_items || 0), 0);
          badge.textContent = `✅ ${data.count || 0} Batches (${totalRecords} Cleaned Malayalam Documents Ready)`;
        }
      }
    } catch (e) {
      console.warn('Failed to fetch approved count:', e);
    }

    // Event listeners
    document.getElementById('btn_copy_colab_script')?.addEventListener('click', () => {
      const preview = document.getElementById('colab_script_preview');
      if (preview) {
        navigator.clipboard.writeText(preview.textContent);
        const st = document.getElementById('colab_copy_status');
        if (st) {
          st.textContent = '✓ Copied script to clipboard!';
          setTimeout(() => { st.textContent = ''; }, 2000);
        }
        this.notify('Colab QLoRA script copied to clipboard!', 'success');
      }
    });

    document.getElementById('btn_download_approved_json')?.addEventListener('click', async () => {
      try {
        const resp = await fetch('/api/dataset/approved');
        if (resp.ok) {
          const data = await resp.json();
          this.exporter.downloadString('malayalam_training_corpus.json', JSON.stringify(data, null, 2));
          this.notify('Exported approved Malayalam corpus dataset!', 'success');
        }
      } catch (e) {
        this.notify('Failed to export dataset: ' + e.message, 'error');
      }
    });

    document.getElementById('btn_fetch_colab_approved')?.addEventListener('click', () => {
      this.renderColabBridgeTabPanel();
    });
  }

  initTopNavActions() {
    // Left Sidebar Drawer Toggle
    const toggleSidebarBtn = document.getElementById('btn_toggle_sidebar');
    const paletteDock = document.getElementById('palette_dock');
    if (toggleSidebarBtn && paletteDock) {
      toggleSidebarBtn.addEventListener('click', () => {
        paletteDock.classList.toggle('collapsed');
        const isCollapsed = paletteDock.classList.contains('collapsed');
        toggleSidebarBtn.classList.toggle('active', !isCollapsed);
        this.notify(`Sidebar ${isCollapsed ? 'hidden' : 'visible'}`, 'info');
      });
    }

    // Global keyboard shortcut Ctrl+B / Cmd+B for sidebar toggle
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleSidebarBtn?.click();
      }
    });

    // Zoom controls
    document.getElementById('btn_zoom_in')?.addEventListener('click', () => {
      this.canvas.setZoom(Math.round(this.canvas.scale * 100) + 15);
    });

    document.getElementById('btn_zoom_out')?.addEventListener('click', () => {
      this.canvas.setZoom(Math.round(this.canvas.scale * 100) - 15);
    });

    document.getElementById('btn_fit_view')?.addEventListener('click', () => {
      this.canvas.fitView();
    });

    document.getElementById('btn_reset_view')?.addEventListener('click', () => {
      this.canvas.resetView();
    });

    // Snapping toggle
    const snapBtn = document.getElementById('btn_toggle_snap');
    if (snapBtn) {
      snapBtn.addEventListener('click', () => {
        this.canvas.snapToGrid = !this.canvas.snapToGrid;
        snapBtn.classList.toggle('active', this.canvas.snapToGrid);
        this.notify(`Grid Snapping: ${this.canvas.snapToGrid ? 'ON' : 'OFF'}`, 'info');
      });
    }

    // Collapsible Toolbar Overflow Dropdown Menu
    const overflowTrigger = document.getElementById('btn_toolbar_overflow');
    const overflowDropdown = document.getElementById('toolbar_overflow_dropdown');
    if (overflowTrigger && overflowDropdown) {
      overflowTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        overflowDropdown.classList.toggle('show');
      });

      document.addEventListener('click', (e) => {
        if (!overflowDropdown.contains(e.target) && e.target !== overflowTrigger) {
          overflowDropdown.classList.remove('show');
        }
      });
    }

    // Overflow Dropdown Actions
    document.getElementById('overflow_snap_grid')?.addEventListener('click', () => {
      document.getElementById('btn_toggle_snap')?.click();
      overflowDropdown?.classList.remove('show');
    });

    document.getElementById('overflow_fit_canvas')?.addEventListener('click', () => {
      this.canvas.fitView();
      overflowDropdown?.classList.remove('show');
    });

    document.getElementById('overflow_reset_view')?.addEventListener('click', () => {
      this.canvas.resetView();
      overflowDropdown?.classList.remove('show');
    });

    document.getElementById('overflow_load_json')?.addEventListener('click', () => {
      document.getElementById('load_json_input')?.click();
      overflowDropdown?.classList.remove('show');
    });

    document.getElementById('overflow_save_json')?.addEventListener('click', () => {
      this.exporter.saveWorkflowJson(this.canvas.getGraphData());
      overflowDropdown?.classList.remove('show');
    });

    document.getElementById('overflow_clear_canvas')?.addEventListener('click', () => {
      document.getElementById('btn_clear_canvas')?.click();
      overflowDropdown?.classList.remove('show');
    });

    // Health pill and header status button open Vault / Diagnostics
    this.healthPill?.addEventListener('click', () => this.openKeyVaultModal());
    this.headerStatusBadge?.addEventListener('click', () => {
      // Switch to diagnostics tab in dock
      const diagTab = document.querySelector('.code-tab[data-tab="diagnostics"]');
      if (diagTab) diagTab.click();
    });
    document.getElementById('btn_open_vault')?.addEventListener('click', () => this.openKeyVaultModal());
    document.getElementById('btn_open_diagnostics')?.addEventListener('click', () => {
      const diagTab = document.querySelector('.code-tab[data-tab="diagnostics"]');
      if (diagTab) diagTab.click();
    });
    document.getElementById('btn_open_review')?.addEventListener('click', () => {
      if (this.codeDrawer.classList.contains('collapsed')) {
        this.codeDrawer.classList.remove('collapsed');
        const toggleDrawerBtn = document.getElementById('toggle_drawer_btn');
        if (toggleDrawerBtn) toggleDrawerBtn.innerHTML = '▼ Minimize';
      }
      const reviewTab = document.querySelector('.code-tab[data-tab="dataset_review"]');
      if (reviewTab) reviewTab.click();
    });

    // Export Complete ZIP
    document.getElementById('btn_export_zip')?.addEventListener('click', () => {
      this.exporter.exportFullZip(this.canvas.getGraphData());
    });

    // Save JSON Workflow
    document.getElementById('btn_save_json')?.addEventListener('click', () => {
      this.exporter.saveWorkflowJson(this.canvas.getGraphData());
    });

    // Load JSON Workflow
    const fileInp = document.getElementById('load_json_input');
    document.getElementById('btn_load_json')?.addEventListener('click', () => {
      if (fileInp) fileInp.click();
    });
    if (fileInp) {
      fileInp.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          this.exporter.loadWorkflowJson(e.target.files[0], (graph) => {
            this.canvas.loadGraph(graph);
            this.refreshCode();
            this.runDiagnostics();
          });
        }
      });
    }

    // Clear Canvas
    document.getElementById('btn_clear_canvas')?.addEventListener('click', () => {
      if (confirm('Clear entire workflow canvas?')) {
        this.canvas.loadGraph({ nodes: [], connections: [] });
        this.refreshCode();
        this.runDiagnostics();
        this.notify('Canvas cleared', 'info');
      }
    });
  }

  getCurrentCodeText() {
    if (this.currentTab === 'native') {
      if (this.currentSubFile === 'agents.yaml') return this.cachedCode.agentsYaml || '';
      if (this.currentSubFile === 'tasks.yaml') return this.cachedCode.tasksYaml || '';
      if (this.currentSubFile === 'crew.py') return this.cachedCode.crewPy || '';
      if (this.currentSubFile === 'main.py') return this.cachedCode.mainPy || '';
    } else if (this.currentTab === 'single') {
      return this.cachedCode.singleRunnerPy || '';
    } else if (this.currentTab === 'env') {
      return this.cachedCode.envFile || '';
    } else if (this.currentTab === 'reqs') {
      return this.cachedCode.requirementsTxt || '';
    }
    return '';
  }

  getCurrentFileName() {
    if (this.currentTab === 'native') return this.currentSubFile;
    if (this.currentTab === 'single') return 'crew_runner.py';
    if (this.currentTab === 'env') return '.env';
    if (this.currentTab === 'reqs') return 'requirements.txt';
    return 'code.txt';
  }

  getLanguageForFile(filename) {
    if (filename.endsWith('.yaml') || filename.endsWith('.yml')) return 'yaml';
    if (filename.endsWith('.py')) return 'python';
    if (filename.endsWith('.env') || filename.endsWith('.txt')) return 'bash';
    return 'plaintext';
  }

  refreshCode() {
    const graph = this.canvas.getGraphData();
    // Pass real user keys to generateCrewProject so .env gets actual configured keys!
    this.cachedCode = generateCrewProject(graph, this.keyVault.keys);
    this.updateCodeDisplay();
  }

  updateCodeDisplay() {
    const text = this.getCurrentCodeText();
    const filename = this.getCurrentFileName();
    const lang = this.getLanguageForFile(filename);

    if (typeof Prism !== 'undefined') {
      const grammar = Prism.languages[lang] || Prism.languages.python;
      this.codeContentEl.innerHTML = Prism.highlight(text, grammar, lang);
    } else {
      this.codeContentEl.textContent = text;
    }
  }

  saveToStorage() {
    try {
      const graph = this.canvas.getGraphData();
      localStorage.setItem('crewai_builder_graph', JSON.stringify(graph));
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }

  loadInitialWorkflow() {
    try {
      // First boot of v2.1 or empty storage -> load 100% Offline Ollama Crew template
      const v21OfflineLoaded = localStorage.getItem('crewai_v21_offline_default_loaded');
      const saved = localStorage.getItem('crewai_builder_graph');

      if (!v21OfflineLoaded || !saved) {
        localStorage.setItem('crewai_v21_offline_default_loaded', 'true');
        this.canvas.loadGraph(WORKFLOW_TEMPLATES.offline_ollama);
        this.refreshCode();
        this.runDiagnostics();
        this.updateVaultPills();
        const tmplSelect = document.getElementById('template_selector');
        if (tmplSelect) tmplSelect.value = 'offline_ollama';
        return;
      }

      if (saved) {
        const graph = JSON.parse(saved);
        if (graph.nodes && graph.nodes.length > 0) {
          this.canvas.loadGraph(graph);
          this.refreshCode();
          this.runDiagnostics();
          this.updateVaultPills();
          return;
        }
      }
    } catch (e) {
      console.warn('LocalStorage restore error:', e);
    }

    // Default to Offline Ollama template
    this.canvas.loadGraph(WORKFLOW_TEMPLATES.offline_ollama);
    this.refreshCode();
    this.runDiagnostics();
    this.updateVaultPills();
    const tmplSelect = document.getElementById('template_selector');
    if (tmplSelect) tmplSelect.value = 'offline_ollama';
  }
}

// Instantiate on DOM ready
window.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
