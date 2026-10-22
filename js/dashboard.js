/**
 * malayaLLM v2.3.0 - Web Operations Center JavaScript Dashboard
 * Pure Vanilla ES6 Modular Client for Autonomous Pipeline Control & HITL Review
 */

class MalayaDashboard {
  constructor() {
    this.pollInterval = 1000; // 1s polling
    this.pollTimer = null;
    this.currentTab = 'pipeline';
    this.reviewFilter = 'pending_approval';
    this.lastLogId = 0;
    this.isAutoScrollLogs = true;

    this.dom = {
      btnMasterPlay: document.getElementById('btn_master_play'),
      btnMasterPlayText: document.getElementById('master_play_text'),
      btnStep: document.getElementById('btn_step'),
      pipelineStatePill: document.getElementById('pipeline_state_pill'),
      pipelineStateText: document.getElementById('pipeline_state_text'),
      
      // KPI elements
      kpiTotalProcessed: document.getElementById('kpi_total_processed'),
      kpiThroughput: document.getElementById('kpi_throughput'),
      kpiAvgDensity: document.getElementById('kpi_avg_density'),
      kpiPendingQueue: document.getElementById('kpi_pending_queue'),

      // Node boxes
      nodeIngestor: document.getElementById('node_ingestor'),
      nodeNormalizer: document.getElementById('node_normalizer'),
      nodeJudge: document.getElementById('node_judge'),
      nodeStaging: document.getElementById('node_staging'),

      countIngestor: document.getElementById('count_ingestor'),
      countNormalizer: document.getElementById('count_normalizer'),
      countJudge: document.getElementById('count_judge'),
      countStaging: document.getElementById('count_staging'),

      // Live Inspector
      inspectorTitle: document.getElementById('inspector_title'),
      inspectorSource: document.getElementById('inspector_source'),
      inspectorEngine: document.getElementById('inspector_engine'),
      rawTextPane: document.getElementById('raw_text_pane'),
      cleanedTextPane: document.getElementById('cleaned_text_pane'),
      gaugeDensity: document.getElementById('gauge_density'),
      gaugeFluency: document.getElementById('gauge_fluency'),
      badgeChilluFixes: document.getElementById('badge_chillu_fixes'),
      badgePiiRedacted: document.getElementById('badge_pii_redacted'),
      inspectorNotes: document.getElementById('inspector_notes'),

      // Terminal
      terminalWindow: document.getElementById('terminal_window'),
      
      // Review Queue
      reviewCardsContainer: document.getElementById('review_cards_container'),
      topPendingBadge: document.getElementById('top_pending_badge'),
      
      // Colab code
      colabScriptViewer: document.getElementById('colab_script_viewer')
    };

    this.init();
  }

  init() {
    this.bindEvents();
    this.startPolling();
    this.loadReviewQueue();
    this.loadKeysStatus();
    this.loadColabScript();
  }

  bindEvents() {
    // Navigation Tabs
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = btn.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Master Controls
    if (this.dom.btnMasterPlay) {
      this.dom.btnMasterPlay.addEventListener('click', () => this.togglePipeline());
    }

    if (this.dom.btnStep) {
      this.dom.btnStep.addEventListener('click', () => this.stepPipeline());
    }

    // Review Filters
    document.querySelectorAll('.btn-filter').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.reviewFilter = btn.dataset.filter;
        this.loadReviewQueue();
      });
    });

    // Bulk Review Actions
    const btnApproveAll = document.getElementById('btn_approve_all');
    if (btnApproveAll) {
      btnApproveAll.addEventListener('click', () => this.approveAllPending());
    }

    const btnSeedDemo = document.getElementById('btn_seed_demo');
    if (btnSeedDemo) {
      btnSeedDemo.addEventListener('click', () => this.seedDemoItems());
    }

    const btnTriggerExport = document.getElementById('btn_trigger_export');
    if (btnTriggerExport) {
      btnTriggerExport.addEventListener('click', () => this.triggerExport());
    }

    const btnCopyColab = document.getElementById('btn_copy_colab');
    if (btnCopyColab) {
      btnCopyColab.addEventListener('click', () => this.copyColabScript());
    }

    // Auto-Proofread with Gemma
    const btnAutoProofread = document.getElementById('btn_auto_proofread_gemma');
    if (btnAutoProofread) {
      btnAutoProofread.addEventListener('click', () => this.autoProofreadQueue());
    }

    // PDF Upload handling
    const btnBrowsePdf = document.getElementById('btn_browse_pdf');
    const pdfFileInput = document.getElementById('pdf_file_input');
    const btnUploadPdf = document.getElementById('btn_upload_pdf');
    const pdfStatus = document.getElementById('pdf_upload_status');

    if (btnBrowsePdf && pdfFileInput) {
      btnBrowsePdf.addEventListener('click', () => pdfFileInput.click());
      pdfFileInput.addEventListener('change', () => {
        if (pdfFileInput.files && pdfFileInput.files[0]) {
          const file = pdfFileInput.files[0];
          if (pdfStatus) {
            pdfStatus.style.display = 'block';
            pdfStatus.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
          }
          if (btnUploadPdf) btnUploadPdf.style.display = 'inline-flex';
        }
      });
    }

    if (btnUploadPdf) {
      btnUploadPdf.addEventListener('click', () => this.uploadPDF());
    }

    // Provider key save forms
    document.querySelectorAll('.btn-save-key').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const provider = btn.dataset.provider;
        this.saveProviderKey(provider);
      });
    });

    document.querySelectorAll('.btn-test-key').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const provider = btn.dataset.provider;
        this.testProviderKey(provider);
      });
    });

    const btnSaveOllama = document.getElementById('btn_save_ollama');
    if (btnSaveOllama) {
      btnSaveOllama.addEventListener('click', () => this.saveOllamaConfig());
    }

    // Per-Phase Play/Pause Controls
    document.querySelectorAll('.phase-toggle-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const phase = btn.dataset.phase;
        try {
          const resp = await fetch('/api/pipeline/phase/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phase })
          });
          if (resp.ok) {
            const res = await resp.json();
            const isEnabled = res.data ? res.data.is_enabled : true;
            btn.classList.toggle('paused', !isEnabled);
            const label = btn.querySelector('.phase-toggle-label');
            if (label) label.textContent = isEnabled ? 'Active' : 'Paused';
            const nodeBox = btn.closest('.node-box');
            if (nodeBox) nodeBox.classList.toggle('phase-paused', !isEnabled);
            this.pollStatus();
          }
        } catch (err) {
          console.error("Phase toggle error:", err);
        }
      });
    });

    // Open Datasets Refresh Button
    const btnSyncOpen = document.getElementById('btn_sync_open_datasets');
    if (btnSyncOpen) {
      btnSyncOpen.addEventListener('click', () => this.syncOpenDatasets());
    }
  }

  switchTab(tabName) {
    this.currentTab = tabName;
    document.querySelectorAll('.nav-tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-pane').forEach(p => {
      p.classList.toggle('active', p.id === `tab_${tabName}`);
    });

    if (tabName === 'review') {
      this.loadReviewQueue();
    } else if (tabName === 'datasets') {
      this.loadOpenDatasets();
    } else if (tabName === 'keys') {
      this.loadKeysStatus();
    } else if (tabName === 'colab') {
      this.loadColabScript();
    }
  }

  // ==========================================
  // Pipeline Real-time Polling & Master Sync
  // ==========================================

  startPolling() {
    this.pollStatus();
    this.pollTimer = setInterval(() => this.pollStatus(), this.pollInterval);
  }

  async pollStatus() {
    try {
      const resp = await fetch('/api/pipeline/status');
      if (!resp.ok) return;
      const data = await resp.json();
      this.updatePipelineUI(data);
    } catch (e) {
      console.warn("Poll failed:", e);
    }
  }

  updatePipelineUI(data) {
    const isRunning = data.is_running;
    const currentPhase = data.current_phase || 'idle';
    const counters = data.counters || {};
    const queueStats = data.queue_stats || {};
    const liveItem = data.live_item || {};

    // 1. Update Master Play/Pause Button
    if (this.dom.btnMasterPlay) {
      if (isRunning) {
        this.dom.btnMasterPlay.classList.add('running');
        this.dom.btnMasterPlayText.textContent = '❚❚ Pause Pipeline';
      } else {
        this.dom.btnMasterPlay.classList.remove('running');
        this.dom.btnMasterPlayText.textContent = '▶ Resume Pipeline';
      }
    }

    // 2. Update Status Pill
    if (this.dom.pipelineStatePill) {
      this.dom.pipelineStatePill.className = `pipeline-state-pill ${isRunning ? 'running' : 'paused'}`;
      this.dom.pipelineStateText.textContent = isRunning ? `RUNNING (${currentPhase.toUpperCase()})` : 'PAUSED';
    }

    // 3. Update KPI Counters
    if (this.dom.kpiTotalProcessed) this.dom.kpiTotalProcessed.textContent = (data.total_items_processed || 0).toLocaleString();
    if (this.dom.kpiThroughput) this.dom.kpiThroughput.textContent = isRunning ? `${data.throughput_per_min || 0} /min` : `0.0 /min (Paused)`;
    if (this.dom.kpiAvgDensity) this.dom.kpiAvgDensity.textContent = `${((queueStats.avg_density || 0.88) * 100).toFixed(1)}%`;
    if (this.dom.kpiPendingQueue) this.dom.kpiPendingQueue.textContent = (queueStats.pending_count || 0).toLocaleString();
    if (this.dom.inspectorEngine && data.active_engine) this.dom.inspectorEngine.textContent = `Active: ${data.active_engine}`;
    if (this.dom.topPendingBadge) {
      this.dom.topPendingBadge.textContent = queueStats.pending_count || 0;
      this.dom.topPendingBadge.style.display = (queueStats.pending_count > 0) ? 'inline-block' : 'none';
    }

    // 4. Update Per-Phase Play/Pause Indicators
    if (data.phase_enabled) {
      Object.entries(data.phase_enabled).forEach(([phase, isEnabled]) => {
        const btn = document.querySelector(`.phase-toggle-btn[data-phase="${phase}"]`);
        if (btn) {
          btn.classList.toggle('paused', !isEnabled);
          const label = btn.querySelector('.phase-toggle-label');
          if (label) label.textContent = isEnabled ? 'Active' : 'Paused';
          const nodeBox = btn.closest('.node-box');
          if (nodeBox) nodeBox.classList.toggle('phase-paused', !isEnabled);
        }
      });
    }

    // 5. Update Node Visual Ring Highlights & Counts
    const totalStaged = (queueStats.total_count !== undefined && queueStats.total_count > 0) ? queueStats.total_count : (counters.judged || 0);
    const nodes = [
      { el: this.dom.nodeIngestor, phase: 'ingestion', countEl: this.dom.countIngestor, count: counters.ingested },
      { el: this.dom.nodeNormalizer, phase: 'normalization', countEl: this.dom.countNormalizer, count: counters.normalized },
      { el: this.dom.nodeJudge, phase: 'judging', countEl: this.dom.countJudge, count: counters.judged },
      { el: this.dom.nodeStaging, phase: 'staging', countEl: this.dom.countStaging, count: totalStaged }
    ];

    nodes.forEach(n => {
      if (n.el) {
        n.el.classList.toggle('active', isRunning && currentPhase === n.phase);
      }
      if (n.countEl && n.count !== undefined) {
        n.countEl.textContent = (n.count || 0).toLocaleString();
      }
    });

    const subApproved = document.getElementById('sub_staging_approved');
    if (subApproved) {
      subApproved.textContent = (counters.approved || queueStats.auto_approved_count || 0).toLocaleString();
    }
    const subPending = document.getElementById('sub_staging_pending');
    if (subPending) {
      subPending.textContent = (queueStats.pending_count || 0).toLocaleString();
    }

    // 5. Update Live Item Inspector
    if (liveItem && liveItem.title) {
      if (this.dom.inspectorTitle) this.dom.inspectorTitle.textContent = liveItem.title;
      if (this.dom.inspectorSource) {
        this.dom.inspectorSource.textContent = liveItem.source || 'Scraped Stream';
        this.dom.inspectorSource.title = liveItem.source || '';
      }
      if (this.dom.rawTextPane) this.dom.rawTextPane.innerHTML = this.escapeHtml(liveItem.raw_text || 'Waiting for stream...');
      if (this.dom.cleanedTextPane) this.dom.cleanedTextPane.innerHTML = this.highlightCleanedText(liveItem.cleaned_text || 'Waiting for processing...');

      const densityVal = (liveItem.malayalam_density || 0) * 100;
      if (this.dom.gaugeDensity) {
        this.dom.gaugeDensity.textContent = `${densityVal.toFixed(1)}%`;
        this.dom.gaugeDensity.className = `gauge-value ${densityVal >= 60 ? 'pass' : 'fail'}`;
      }

      const fluencyVal = liveItem.fluency_score || 1.0;
      if (this.dom.gaugeFluency) {
        this.dom.gaugeFluency.textContent = `${(fluencyVal * 100).toFixed(0)}%`;
        this.dom.gaugeFluency.className = `gauge-value ${fluencyVal >= 0.7 ? 'pass' : 'fail'}`;
      }

      if (this.dom.badgeChilluFixes) this.dom.badgeChilluFixes.textContent = liveItem.chillu_fixes || 0;
      if (this.dom.badgePiiRedacted) this.dom.badgePiiRedacted.textContent = liveItem.pii_redacted || 0;
    }

    // 6. Update Live Terminal
    if (data.logs && data.logs.length > 0) {
      this.renderLogs(data.logs);
    }
  }

  renderLogs(logs) {
    if (!this.dom.terminalWindow) return;
    this.dom.terminalWindow.innerHTML = '';
    logs.forEach(log => {
      const line = document.createElement('div');
      line.className = 'log-entry';
      line.innerHTML = `
        <span class="log-time">[${log.timestamp ? log.timestamp.split(' ')[1] : ''}]</span>
        <span class="log-level ${log.level}">${log.level}</span>
        <span class="log-msg">${this.escapeHtml(log.message)}</span>
      `;
      this.dom.terminalWindow.appendChild(line);
    });

    if (this.isAutoScrollLogs) {
      this.dom.terminalWindow.scrollTop = this.dom.terminalWindow.scrollHeight;
    }
  }

  highlightCleanedText(text) {
    if (!text) return '';
    let formatted = this.escapeHtml(text);
    formatted = formatted.replace(/\[EMAIL_REDACTED\]/g, '<span class="redacted-tag">[EMAIL]</span>');
    formatted = formatted.replace(/\[PHONE_REDACTED\]/g, '<span class="redacted-tag">[PHONE]</span>');
    formatted = formatted.replace(/\[AADHAAR_REDACTED\]/g, '<span class="redacted-tag">[AADHAAR]</span>');
    formatted = formatted.replace(/\[PAN_REDACTED\]/g, '<span class="redacted-tag">[PAN]</span>');
    return formatted;
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async togglePipeline() {
    try {
      const resp = await fetch('/api/pipeline/status');
      const data = await resp.json();
      const endpoint = data.is_running ? '/api/pipeline/pause' : '/api/pipeline/start';
      await fetch(endpoint, { method: 'POST' });
      this.pollStatus();
    } catch (e) {
      console.error("Failed to toggle pipeline:", e);
    }
  }

  async stepPipeline() {
    try {
      await fetch('/api/pipeline/step', { method: 'POST' });
      this.pollStatus();
    } catch (e) {
      console.error("Step execution failed:", e);
    }
  }

  // ==========================================
  // Tab 2: Human Review Queue
  // ==========================================

  async loadReviewQueue() {
    if (!this.dom.reviewCardsContainer) return;
    try {
      const fetchStatus = (this.reviewFilter === 'open_dataset') ? 'all' : this.reviewFilter;
      const resp = await fetch(`/api/queue/review?status=${fetchStatus}&limit=100`);
      if (!resp.ok) return;
      const data = await resp.json();
      let items = data.items || [];
      if (this.reviewFilter === 'open_dataset') {
        items = items.filter(item => {
          const s = (item.source || '').toLowerCase();
          const t = (item.title || '').toLowerCase();
          return s.includes('open_') || s.includes('alpaca') || s.includes('culturax') || s.includes('wiki') || s.includes('indic') || s.includes('jsonl') || t.includes('alpaca') || t.includes('culturax') || t.includes('wikipedia');
        });
      }
      this.renderReviewCards(items);
    } catch (e) {
      console.error("Failed to load review queue:", e);
    }
  }

  renderReviewCards(items) {
    this.dom.reviewCardsContainer.innerHTML = '';
    if (items.length === 0) {
      this.dom.reviewCardsContainer.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-dim);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🎉</div>
          <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-muted);">No items in this queue filter</div>
          <div style="font-size: 0.85rem; margin-top: 4px;">Click "Seed Demo Batches" or resume the pipeline to ingest more records.</div>
        </div>
      `;
      return;
    }

    items.forEach(item => {
      const card = document.createElement('div');
      card.className = `review-card ${item.status}`;
      card.id = `card_${item.item_id}`;

      const densityPct = ((item.malayalam_density || 0) * 100).toFixed(1);
      const fluencyScore = ((item.fluency_score || 1.0) * 100).toFixed(0);
      const confScore = item.confidence_score ? (item.confidence_score * 100).toFixed(1) : null;
      const isAutoApproved = Boolean(item.auto_approved);

      card.innerHTML = `
        <div class="review-card-header">
          <div class="review-card-title">
            <span>${this.escapeHtml(item.title || 'Malayalam Record')}</span>
            ${isAutoApproved ? `<span class="status-tag auto-approved">⚡ Auto-Approved (≥85%)</span>` : `<span class="status-tag ${item.status}">${item.status.replace('_', ' ')}</span>`}
          </div>
          <a href="${this.escapeHtml(item.source)}" target="_blank" class="inspector-source-pill">
            ${this.escapeHtml(item.source || 'Scraped Source')}
          </a>
        </div>

        <div class="review-metrics-badges">
          ${confScore ? `<span class="metric-badge ${item.confidence_score >= 0.85 ? 'green' : 'purple'}">🎯 Gemma Conf: ${confScore}%</span>` : ''}
          <span class="metric-badge green">Unicode Density: ${densityPct}%</span>
          <span class="metric-badge cyan">Fluency: ${fluencyScore}% (${this.escapeHtml(item.quality_rating || 'High')})</span>
          <span class="metric-badge">Chillus Fixed: ${item.chillu_fixes || 0}</span>
          <span class="metric-badge">PII Redacted: ${item.pii_redacted || 0}</span>
        </div>

        <div class="review-card-body">
          <div class="text-pane">
            <div class="pane-label">Original Raw Harvested Text</div>
            <div class="review-text-box">${this.escapeHtml(item.raw_text)}</div>
          </div>
          <div class="text-pane">
            <div class="pane-label">
              <span>Cleaned & Normalized Text (Editable)</span>
              ${item.gemma_proofread_text && item.gemma_proofread_text !== item.cleaned_text ? `
                <button style="font-size: 0.68rem; background: rgba(139, 92, 246, 0.2); color: var(--accent-violet); border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 4px; padding: 2px 6px; cursor: pointer;" onclick="document.getElementById('edit_text_${item.item_id}').value = ${JSON.stringify(item.gemma_proofread_text)};">
                  ✨ Use Gemma Suggestion
                </button>
              ` : `<span style="font-size: 0.68rem; color: var(--accent-emerald);">UTF-8 Enforced</span>`}
            </div>
            <textarea class="review-text-box key-textarea" id="edit_text_${item.item_id}" style="height: 160px; font-family: var(--font-sans); font-size: 0.88rem;">${this.escapeHtml(item.cleaned_text)}</textarea>
          </div>
        </div>

        <div class="review-actions-bar">
          ${item.status === 'pending_approval' ? `
            <button class="btn-reject" onclick="dashboard.performAction('${item.item_id}', 'reject')">
              <span>✕</span> Reject & Discard
            </button>
            <button class="btn-approve" onclick="dashboard.performAction('${item.item_id}', 'approve')">
              <span>✓</span> Approve & Push to Training
            </button>
          ` : `
            <span style="font-size: 0.8rem; color: var(--text-dim);">
              Status locked (${item.status}). Reviewed at: ${item.reviewed_at ? item.reviewed_at.split('T')[0] : 'Just now'} ${item.reviewer_notes ? `• ${this.escapeHtml(item.reviewer_notes)}` : ''}
            </span>
          `}
        </div>
      `;
      this.dom.reviewCardsContainer.appendChild(card);
    });
  }

  async performAction(itemId, action) {
    try {
      const editInput = document.getElementById(`edit_text_${itemId}`);
      const editedText = editInput ? editInput.value : undefined;

      const resp = await fetch('/api/queue/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonSafeStringify({
          item_id: itemId,
          action: action,
          edited_cleaned_text: editedText
        })
      });

      if (resp.ok) {
        const card = document.getElementById(`card_${itemId}`);
        if (card) {
          card.classList.add(action === 'approve' ? 'approved' : 'rejected');
          card.style.transform = 'scale(0.98)';
          setTimeout(() => this.loadReviewQueue(), 400);
        }
        this.pollStatus();
      }
    } catch (e) {
      console.error("Action failed:", e);
    }
  }

  async approveAllPending() {
    try {
      const resp = await fetch('/api/queue/review?status=pending_approval&limit=100');
      const data = await resp.json();
      const items = data.items || [];
      const itemIds = items.map(i => i.item_id);

      if (itemIds.length === 0) {
        alert("No pending items to approve.");
        return;
      }

      await fetch('/api/queue/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonSafeStringify({
          item_ids: itemIds,
          action: 'approve'
        })
      });

      this.loadReviewQueue();
      this.pollStatus();
    } catch (e) {
      console.error("Approve all failed:", e);
    }
  }

  async seedDemoItems() {
    try {
      await fetch('/api/queue/seed_demo', { method: 'POST' });
      this.loadReviewQueue();
      this.pollStatus();
    } catch (e) {
      console.error("Seed demo failed:", e);
    }
  }

  async autoProofreadQueue() {
    const btn = document.getElementById('btn_auto_proofread_gemma');
    const oldText = btn ? btn.innerHTML : '';
    try {
      if (btn) {
        btn.innerHTML = '<span>⏳</span> Proofreading with Gemma...';
        btn.disabled = true;
      }
      const resp = await fetch('/api/queue/auto_proofread', { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Gemma Proofreading Complete!\nTotal Evaluated: ${data.result.total_scanned}\nAuto-Approved (≥85%): ${data.result.auto_approved}\nRetained in HITL (<85%): ${data.result.remaining_pending}`);
        this.loadReviewQueue();
        this.pollStatus();
      } else {
        alert("Proofread failed: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      alert("Error during Gemma proofreading: " + e);
    } finally {
      if (btn) {
        btn.innerHTML = oldText;
        btn.disabled = false;
      }
    }
  }

  async uploadPDF() {
    const fileInput = document.getElementById('pdf_file_input');
    const statusEl = document.getElementById('pdf_upload_status');
    const btnUpload = document.getElementById('btn_upload_pdf');
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
      alert("Please select a PDF file first.");
      return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.textContent = `Extracting & cleaning ${file.name}... (stripping watermarks, page headers)`;
      }
      if (btnUpload) btnUpload.disabled = true;

      const resp = await fetch('/api/ingest/upload_pdf', {
        method: 'POST',
        body: formData
      });
      const data = await resp.json();

      if (data.success) {
        if (statusEl) {
          statusEl.textContent = `✓ ${data.message}`;
          statusEl.style.color = 'var(--accent-emerald)';
        }
        alert(`✓ Malayalam PDF Processed!\nFile: ${data.filename}\nExtracted Chunks: ${data.chunks_extracted}\nChunks are now prioritized in the ingestion queue!`);
        fileInput.value = '';
        if (btnUpload) btnUpload.style.display = 'none';
        this.pollStatus();
      } else {
        if (statusEl) {
          statusEl.textContent = `Error: ${data.detail || 'Upload failed'}`;
          statusEl.style.color = 'var(--accent-rose)';
        }
      }
    } catch (e) {
      alert("Upload error: " + e);
    } finally {
      if (btnUpload) btnUpload.disabled = false;
    }
  }

  // ==========================================
  // Tab 3: Key Rotator & Credentials
  // ==========================================

  async loadKeysStatus() {
    try {
      const resp = await fetch('/api/keys');
      if (!resp.ok) return;
      const data = await resp.json();
      const providers = data.providers || {};

      ['groq', 'gemini', 'openrouter', 'nvidia'].forEach(prov => {
        const pData = providers[prov];
        const badge = document.getElementById(`badge_${prov}_keys`);
        if (badge && pData) {
          badge.textContent = `${pData.available_keys}/${pData.total_keys} Active`;
        }
      });

      if (data.ollama) {
        const endpointInput = document.getElementById('input_ollama_endpoint');
        const modelInput = document.getElementById('input_ollama_model');
        if (endpointInput) endpointInput.value = data.ollama.endpoint || 'http://localhost:11434';
        if (modelInput) modelInput.value = data.ollama.model || 'llama3.2';
      }
    } catch (e) {
      console.error("Failed to load keys status:", e);
    }
  }

  async saveProviderKey(provider) {
    const input = document.getElementById(`input_key_${provider}`);
    if (!input) return;
    const rawKeys = input.value;

    try {
      const resp = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonSafeStringify({
          provider: provider,
          keys: rawKeys,
          test_after_save: false
        })
      });
      const data = await resp.json();
      if (data.success) {
        alert(`Successfully saved ${data.total_saved} key(s) for ${provider.toUpperCase()}`);
        input.value = '';
        this.loadKeysStatus();
      }
    } catch (e) {
      alert(`Failed to save key: ${e}`);
    }
  }

  async testProviderKey(provider) {
    const input = document.getElementById(`input_key_${provider}`);
    const key = input ? input.value.trim() : '';

    try {
      const resp = await fetch('/api/keys/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonSafeStringify({ provider: provider, key: key })
      });
      const data = await resp.json();
      alert(`[${provider.toUpperCase()}] Result: ${data.message}`);
    } catch (e) {
      alert(`Test connection error: ${e}`);
    }
  }

  async saveOllamaConfig() {
    const endpoint = document.getElementById('input_ollama_endpoint').value;
    const model = document.getElementById('input_ollama_model').value;
    try {
      const resp = await fetch('/api/keys/ollama_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonSafeStringify({ endpoint: endpoint, model: model })
      });
      if (resp.ok) {
        alert("Ollama configuration updated successfully!");
        this.loadKeysStatus();
      }
    } catch (e) {
      alert(`Failed to update Ollama: ${e}`);
    }
  }

  // ==========================================
  // Tab 4: Training & Google Colab Bridge
  // ==========================================

  async triggerExport() {
    try {
      const resp = await fetch('/api/export/trigger', { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Training Dataset Exported!\nTotal records: ${data.total_records}\nJSONL: ${data.files.jsonl}\nColab Script: ${data.files.colab_script}`);
        this.loadColabScript();
      }
    } catch (e) {
      alert(`Export failed: ${e}`);
    }
  }

  async loadColabScript() {
    if (!this.dom.colabScriptViewer) return;
    try {
      const resp = await fetch('/api/training/colab_script');
      if (resp.ok) {
        const text = await resp.text();
        this.dom.colabScriptViewer.textContent = text;
      }
    } catch (e) {
      console.error("Failed to load colab script:", e);
    }
  }

  copyColabScript() {
    if (!this.dom.colabScriptViewer) return;
    navigator.clipboard.writeText(this.dom.colabScriptViewer.textContent).then(() => {
      alert("✓ Google Colab QLoRA Script copied to clipboard!");
    }).catch(e => {
      alert("Failed to copy script.");
    });
  }

  // ==========================================
  // Tab: Open Datasets Library
  // ==========================================

  async loadOpenDatasets() {
    const container = document.getElementById('open_datasets_container');
    if (!container) return;
    try {
      const resp = await fetch('/api/datasets/open_sources');
      if (!resp.ok) return;
      const data = await resp.json();
      const manifest = data.manifest || {};
      this.renderOpenDatasets(manifest);
    } catch (err) {
      console.error("Failed to load open datasets:", err);
    }
  }

  renderOpenDatasets(manifest) {
    const container = document.getElementById('open_datasets_container');
    if (!container) return;
    const datasets = manifest.datasets || {};
    const keys = Object.keys(datasets);
    if (keys.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding: 2rem; color: var(--text-dim);">No open datasets found. Click 'Refresh / Sync Datasets'.</div>`;
      return;
    }

    container.innerHTML = '';
    keys.forEach(k => {
      const d = datasets[k];
      const card = document.createElement('div');
      card.className = 'open-dataset-card';
      const isReady = d.status === 'ready' || d.status === 'ready_for_training';
      const isGated = d.status === 'gated_requires_hf_login';
      const badgeClass = isReady ? 'ready' : (isGated ? 'gated' : 'commercial');
      const badgeText = isReady ? '✓ Ready (Downloaded)' : (isGated ? '🔒 HF Gated' : 'ℹ Curated');

      card.innerHTML = `
        <div>
          <div class="dataset-card-top">
            <div>
              <div class="dataset-card-title">${this.escapeHtml(k.replace(/_/g, ' '))}</div>
              <span style="font-size: 0.72rem; color: var(--text-muted);">${this.escapeHtml(d.type || '')}</span>
            </div>
            <span class="dataset-badge ${badgeClass}">${badgeText}</span>
          </div>
          <div class="dataset-meta-list">
            <div><strong>Source:</strong> <a href="${d.source}" target="_blank" style="color: var(--accent-cyan); text-decoration: none;">${this.escapeHtml(d.source)}</a></div>
            ${d.records_cached !== undefined ? `<div><strong>Records Cached:</strong> <code style="color: var(--accent-emerald);">${d.records_cached}</code></div>` : ''}
            ${d.local_path ? `<div><strong>Local File:</strong> <code>${this.escapeHtml(d.local_path)}</code></div>` : ''}
            ${d.file_size_bytes ? `<div><strong>Size:</strong> ${(d.file_size_bytes / 1024).toFixed(1)} KB</div>` : ''}
            ${d.instructions ? `<div style="color: var(--accent-amber); margin-top: 4px;"><em>${this.escapeHtml(d.instructions)}</em></div>` : ''}
          </div>
        </div>
        <div class="dataset-card-actions">
          ${d.sample_record ? `
            <button class="btn-secondary" style="font-size: 0.75rem; padding: 0.4rem 0.8rem;" onclick="dashboard.previewDatasetSample('${k}')">
              <span>👁</span> Inspect Sample
            </button>
          ` : ''}
          ${d.local_path ? `
            <a href="/data/sources/open_datasets/${d.local_path.split('/').pop()}" download class="btn-primary" style="font-size: 0.75rem; padding: 0.4rem 0.8rem; text-decoration: none;">
              <span>⬇</span> Download JSONL
            </a>
          ` : ''}
        </div>
      `;
      container.appendChild(card);
    });

    this._datasetsManifest = manifest;
    for (const k of keys) {
      if (datasets[k].sample_record) {
        this.previewDatasetSample(k);
        break;
      }
    }
  }

  previewDatasetSample(datasetKey) {
    if (!this._datasetsManifest || !this._datasetsManifest.datasets) return;
    const d = this._datasetsManifest.datasets[datasetKey];
    if (!d) return;

    const viewer = document.getElementById('dataset_sample_content');
    const srcLabel = document.getElementById('dataset_sample_source');

    if (srcLabel) {
      srcLabel.textContent = d.local_path || d.source;
    }

    if (viewer) {
      if (d.sample_record) {
        viewer.textContent = JSON.stringify(d.sample_record, null, 2);
      } else {
        viewer.textContent = `No local sample cached yet for ${datasetKey}.`;
      }
    }
  }

  async syncOpenDatasets() {
    const btn = document.getElementById('btn_sync_open_datasets');
    if (btn) btn.textContent = '⏳ Syncing Open Datasets...';
    try {
      const resp = await fetch('/api/datasets/import_open_sources', { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Open Datasets Synchronized!\nTotal Records: ${data.total_imported}\nAlpaca Instruct: ${data.alpaca_count}\nCulturaX: ${data.culturax_count}\nWikipedia: ${data.wiki_count}`);
        this.loadOpenDatasets();
      }
    } catch (err) {
      alert(`Sync failed: ${err}`);
    } finally {
      if (btn) btn.innerHTML = '<span>🔄</span> Refresh / Sync Datasets';
    }
  }
}

function jsonSafeStringify(obj) {
  return JSON.stringify(obj);
}

// Instantiate dashboard on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.dashboard = new MalayaDashboard();
});
