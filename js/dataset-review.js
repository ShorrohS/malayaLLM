/**
 * Visual CrewAI Studio - Malayalam Dataset Review Queue
 * Human-in-the-Loop Approval Dashboard, Side-by-Side Normalization Viewer & Colab Bridge
 */

export class DatasetReviewManager {
  constructor(containerEl, callbacks = {}) {
    this.containerEl = containerEl;
    this.callbacks = callbacks; // onNotify, onApprovedCountChanged
    this.pendingBatches = [];
    this.approvedBatches = [];
    this.activeBatchId = null;
    this.isLoading = false;
  }

  async loadDatasets() {
    this.isLoading = true;
    try {
      const [pendingRes, approvedRes] = await Promise.all([
        fetch('/api/dataset/pending', { cache: 'no-store' }),
        fetch('/api/dataset/approved', { cache: 'no-store' })
      ]);

      const pendingData = await pendingRes.json();
      const approvedData = await approvedRes.json();

      this.pendingBatches = pendingData.batches || [];
      this.approvedBatches = approvedData.batches || [];

      if (!this.activeBatchId && this.pendingBatches.length > 0) {
        this.activeBatchId = this.pendingBatches[0].id;
      }

      if (this.callbacks.onApprovedCountChanged) {
        this.callbacks.onApprovedCountChanged(this.pendingBatches.length, this.approvedBatches.length);
      }
    } catch (e) {
      console.error('Failed to load datasets:', e);
      if (this.callbacks.onNotify) {
        this.callbacks.onNotify('Could not connect to Dataset API backend', 'error');
      }
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async approveBatch(batchId, notes = '') {
    try {
      const res = await fetch('/api/dataset/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId, notes, timestamp: new Date().toISOString() })
      });
      const data = await res.json();
      if (data.success) {
        if (this.callbacks.onNotify) {
          this.callbacks.onNotify(`✅ Batch ${batchId} approved and moved to training storage!`, 'success');
        }
        await this.loadDatasets();
      } else {
        throw new Error(data.error || 'Failed to approve batch');
      }
    } catch (e) {
      if (this.callbacks.onNotify) this.callbacks.onNotify(`Approval failed: ${e.message}`, 'error');
    }
  }

  async rejectBatch(batchId, feedback = '') {
    try {
      const res = await fetch('/api/dataset/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId, feedback, timestamp: new Date().toISOString() })
      });
      const data = await res.json();
      if (data.success) {
        if (this.callbacks.onNotify) {
          this.callbacks.onNotify(`Batch ${batchId} rejected and logged to feedback queue`, 'info');
        }
        await this.loadDatasets();
      } else {
        throw new Error(data.error || 'Failed to reject batch');
      }
    } catch (e) {
      if (this.callbacks.onNotify) this.callbacks.onNotify(`Rejection failed: ${e.message}`, 'error');
    }
  }

  async reseedDemo() {
    try {
      const res = await fetch('/api/dataset/seed_demo', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        if (this.callbacks.onNotify) this.callbacks.onNotify('Demo Malayalam batches seeded!', 'success');
        await this.loadDatasets();
      }
    } catch (e) {
      if (this.callbacks.onNotify) this.callbacks.onNotify('Seed failed', 'error');
    }
  }

  exportApprovedJSON() {
    if (this.approvedBatches.length === 0) {
      if (this.callbacks.onNotify) this.callbacks.onNotify('No approved datasets available yet to export', 'warning');
      return;
    }

    const trainingData = [];
    this.approvedBatches.forEach(b => {
      b.items.forEach(it => {
        trainingData.push({
          instruction: `മലയാളത്തിൽ സംഗ്രഹിക്കുക അല്ലെങ്കിൽ വ്യാഖ്യാനിക്കുക: ${it.title}`,
          input: "",
          output: it.cleaned_text,
          metadata: {
            source: b.source,
            density: it.malayalam_density,
            fluency: it.fluency_score,
            batch: b.id
          }
        });
      });
    });

    const blob = new Blob([JSON.stringify(trainingData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `malayalam_approved_training_dataset_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    if (this.callbacks.onNotify) this.callbacks.onNotify(`Exported ${trainingData.length} approved training records!`, 'success');
  }

  render() {
    if (!this.containerEl) return;

    const totalPending = this.pendingBatches.length;
    const totalApproved = this.approvedBatches.length;
    const activeBatch = this.pendingBatches.find(b => b.id === this.activeBatchId) || this.pendingBatches[0];

    let overallAvgDensity = 0;
    let overallAvgFluency = 0;
    if (this.pendingBatches.length > 0) {
      const sumDensity = this.pendingBatches.reduce((acc, b) => acc + (b.avg_density || 0), 0);
      const sumFluency = this.pendingBatches.reduce((acc, b) => acc + (b.avg_fluency || 0), 0);
      overallAvgDensity = (sumDensity / this.pendingBatches.length).toFixed(3);
      overallAvgFluency = (sumFluency / this.pendingBatches.length).toFixed(3);
    }

    this.containerEl.innerHTML = `
      <div class="hitl-dashboard">
        <!-- Top KPI Metric Cards -->
        <div class="hitl-kpi-row">
          <div class="kpi-card">
            <span class="kpi-icon">📋</span>
            <div class="kpi-info">
              <span class="kpi-val">${totalPending}</span>
              <span class="kpi-label">Pending Batches</span>
            </div>
          </div>
          <div class="kpi-card approved">
            <span class="kpi-icon">✅</span>
            <div class="kpi-info">
              <span class="kpi-val">${totalApproved}</span>
              <span class="kpi-label">Approved for Training</span>
            </div>
          </div>
          <div class="kpi-card">
            <span class="kpi-icon">📊</span>
            <div class="kpi-info">
              <span class="kpi-val">${overallAvgDensity > 0 ? (overallAvgDensity * 100).toFixed(1) + '%' : 'N/A'}</span>
              <span class="kpi-label">Avg Malayalam Density</span>
            </div>
          </div>
          <div class="kpi-card">
            <span class="kpi-icon">🎯</span>
            <div class="kpi-info">
              <span class="kpi-val">${overallAvgFluency > 0 ? overallAvgFluency : 'N/A'}</span>
              <span class="kpi-label">Avg Fluency Rating</span>
            </div>
          </div>
          <div class="hitl-actions-kpi">
            <button class="btn btn-secondary btn-sm" id="btn_reseed_demo" title="Reseed demo pending batches">
              🔄 Reseed Demo
            </button>
            <button class="btn btn-primary btn-sm" id="btn_export_training" title="Download approved training records as JSON for Colab / Hugging Face">
              ⚡ Export Dataset
            </button>
          </div>
        </div>

        <!-- Main Split Workspace: Left Batches List | Right Side-by-Side Review -->
        <div class="hitl-split-workspace">
          
          <!-- Left: Pending Batches Rail -->
          <div class="hitl-batch-rail">
            <div class="hitl-rail-header">
              <span style="font-weight: 700; font-size: 0.82rem; color: var(--text-main);">Pending Batches</span>
              <span class="badge-count active">${totalPending}</span>
            </div>
            <div class="hitl-rail-list">
              ${totalPending === 0 ? `
                <div class="empty-batch-box">
                  <span>🎉</span>
                  <p>All pending batches reviewed!</p>
                  <button class="btn btn-secondary btn-sm" id="btn_empty_reseed">Seed Demo Batches</button>
                </div>
              ` : this.pendingBatches.map(b => `
                <div class="hitl-batch-item ${activeBatch && activeBatch.id === b.id ? 'active' : ''}" data-batch-id="${b.id}">
                  <div class="hitl-batch-item-title">${b.name}</div>
                  <div class="hitl-batch-item-sub">
                    <span>${b.total_records} docs</span> • 
                    <span>Density: ${(b.avg_density * 100).toFixed(0)}%</span> • 
                    <span>Fluency: ${b.avg_fluency}</span>
                  </div>
                  <div class="hitl-batch-timestamp">${b.timestamp || 'Recent'}</div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Right: Side-by-Side Inspection & Approval View -->
          <div class="hitl-detail-panel">
            ${!activeBatch ? `
              <div class="hitl-no-selection">
                <span>👈</span>
                <p>Select a pending batch from the list to review raw and normalized Malayalam text.</p>
              </div>
            ` : `
              <div class="hitl-detail-header">
                <div>
                  <h3 class="hitl-detail-title">${activeBatch.name}</h3>
                  <div class="hitl-detail-meta">
                    <span>Source: <a href="${activeBatch.source}" target="_blank" rel="noreferrer">${activeBatch.source}</a></span>
                    <span class="meta-pill">Malayalam Block: U+0D00-U+0D7F</span>
                    <span class="meta-pill">NFKC Normalized</span>
                    <span class="meta-pill">Chillus: ൺ,ൻ,ർ,ൽ,ൾ,ൿ</span>
                  </div>
                </div>
                <div class="hitl-action-buttons">
                  <button class="btn btn-secondary btn-sm" id="btn_reject_batch" data-batch-id="${activeBatch.id}">
                    ❌ Reject & Log Feedback
                  </button>
                  <button class="btn btn-primary btn-sm" id="btn_approve_batch" data-batch-id="${activeBatch.id}">
                    ✅ Approve & Move to Training
                  </button>
                </div>
              </div>

              <!-- Document Items List -->
              <div class="hitl-items-scroll">
                ${activeBatch.items.map((it, idx) => `
                  <div class="hitl-doc-card">
                    <div class="hitl-doc-header">
                      <span class="doc-idx-badge">#${idx + 1}</span>
                      <span class="doc-title">${it.title}</span>
                      <div class="doc-metrics">
                        <span class="metric-pill ${it.density_passed ? 'pass' : 'fail'}">
                          Density: ${(it.malayalam_density * 100).toFixed(1)}%
                        </span>
                        <span class="metric-pill info">
                          Chillus Fixed: ${it.chillu_fixes}
                        </span>
                        <span class="metric-pill pii">
                          PII Redacted: ${it.pii_redacted}
                        </span>
                        <span class="metric-pill ${it.passed_validation ? 'pass' : 'warning'}">
                          Fluency: ${it.fluency_score} (${it.quality_rating})
                        </span>
                      </div>
                    </div>

                    <!-- Side-by-Side View -->
                    <div class="hitl-comparison-grid">
                      <div class="comparison-column raw">
                        <div class="column-header">
                          <span>🌐 Raw Scraped Web Text (HTML & Broken Chillus)</span>
                        </div>
                        <div class="text-content raw-text">${this.escapeHtml(it.raw_text)}</div>
                      </div>

                      <div class="comparison-column cleaned">
                        <div class="column-header">
                          <span>✨ Morphologically Normalized & Sanitized Malayalam</span>
                        </div>
                        <div class="text-content cleaned-text">${this.escapeHtml(it.cleaned_text)}</div>
                      </div>
                    </div>

                    ${it.audit_notes && it.audit_notes.length > 0 ? `
                      <div class="hitl-audit-notes">
                        <span style="font-weight: 700; color: var(--text-dim);">Linguistic Critic Notes:</span>
                        ${it.audit_notes.map(n => `<span class="audit-note-item">• ${n}</span>`).join(' ')}
                      </div>
                    ` : ''}
                  </div>
                `).join('')}
              </div>
            `}
          </div>

        </div>
      </div>
    `;

    // Bind Event Listeners
    this.containerEl.querySelector('#btn_reseed_demo')?.addEventListener('click', () => this.reseedDemo());
    this.containerEl.querySelector('#btn_empty_reseed')?.addEventListener('click', () => this.reseedDemo());
    this.containerEl.querySelector('#btn_export_training')?.addEventListener('click', () => this.exportApprovedJSON());

    // Batch rail clicks
    this.containerEl.querySelectorAll('.hitl-batch-item').forEach(el => {
      el.addEventListener('click', () => {
        this.activeBatchId = el.dataset.batchId;
        this.render();
      });
    });

    // Approve button
    const approveBtn = this.containerEl.querySelector('#btn_approve_batch');
    if (approveBtn) {
      approveBtn.addEventListener('click', () => {
        const batchId = approveBtn.dataset.batchId;
        this.approveBatch(batchId);
      });
    }

    // Reject button
    const rejectBtn = this.containerEl.querySelector('#btn_reject_batch');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        const batchId = rejectBtn.dataset.batchId;
        const reason = prompt('Please enter rejection feedback or reason (e.g. Translationese, Low density, Inaccurate content):', 'Contains machine translation artifacts');
        if (reason !== null) {
          this.rejectBatch(batchId, reason);
        }
      });
    }
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
}
