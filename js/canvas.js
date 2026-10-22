/**
 * Visual CrewAI Agent & Workflow Builder
 * Interactive Node Canvas Engine
 * Supports pan, zoom, grid snap, bezier curves, drag-connect, and minimap
 */

import { NODE_TYPES } from './nodes.js';

export class CanvasEngine {
  constructor(containerEl, worldEl, svgEl, minimapCanvasEl, callbacks = {}) {
    this.container = containerEl;
    this.world = worldEl;
    this.svg = svgEl;
    this.minimapCanvas = minimapCanvasEl;
    this.minimapCtx = this.minimapCanvas ? this.minimapCanvas.getContext('2d') : null;
    this.callbacks = callbacks; // onSelectNode, onUpdateGraph, onConnect, etc.

    // Viewport transform state
    this.scale = 1;
    this.panX = 100;
    this.panY = 60;
    this.minScale = 0.3;
    this.maxScale = 2.5;

    // Interaction states
    this.isPanning = false;
    this.panStartX = 0;
    this.panStartY = 0;
    this.spacePressed = false;
    this.snapToGrid = true;
    this.gridSize = 20;

    // Node dragging
    this.draggedNode = null;
    this.dragOffset = { x: 0, y: 0 };

    // Port connecting
    this.connecting = false;
    this.connectSource = null; // { nodeId, portType, portDir, element }
    this.mouseWorldPos = { x: 0, y: 0 };
    this.previewPath = null;

    // Graph state
    this.nodes = [];
    this.connections = [];
    this.selectedNodeId = null;

    this.initEvents();
    this.applyTransform();
  }

  initEvents() {
    // Pan via middle mouse or background drag
    this.container.addEventListener('mousedown', (e) => {
      if (e.target === this.container || e.target.classList.contains('canvas-grid') || e.target === this.svg || this.spacePressed || e.button === 1) {
        this.isPanning = true;
        this.panStartX = e.clientX - this.panX;
        this.panStartY = e.clientY - this.panY;
        this.container.classList.add('panning');
        e.preventDefault();
      }
    });

    window.addEventListener('mousemove', (e) => {
      // Handle panning
      if (this.isPanning) {
        this.panX = e.clientX - this.panStartX;
        this.panY = e.clientY - this.panStartY;
        this.applyTransform();
        return;
      }

      // Convert mouse to world coordinates
      const rect = this.container.getBoundingClientRect();
      this.mouseWorldPos = {
        x: (e.clientX - rect.left - this.panX) / this.scale,
        y: (e.clientY - rect.top - this.panY) / this.scale
      };

      // Handle node dragging
      if (this.draggedNode) {
        let newX = this.mouseWorldPos.x - this.dragOffset.x;
        let newY = this.mouseWorldPos.y - this.dragOffset.y;

        if (this.snapToGrid) {
          newX = Math.round(newX / this.gridSize) * this.gridSize;
          newY = Math.round(newY / this.gridSize) * this.gridSize;
        }

        this.draggedNode.x = newX;
        this.draggedNode.y = newY;
        this.updateNodePosition(this.draggedNode);
        this.renderConnections();
        this.renderMinimap();
        if (this.callbacks.onNodeMoved) this.callbacks.onNodeMoved(this.draggedNode);
      }

      // Handle port connecting preview line
      if (this.connecting && this.connectSource) {
        this.updatePreviewPath();
      }
    });

    window.addEventListener('mouseup', (e) => {
      if (this.isPanning) {
        this.isPanning = false;
        this.container.classList.remove('panning');
      }

      if (this.draggedNode) {
        this.draggedNode = null;
        if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
      }

      if (this.connecting) {
        this.endConnecting(e);
      }
    });

    // Spacebar for panning toggle
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !this.spacePressed && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        this.spacePressed = true;
        this.container.style.cursor = 'grab';
      }
    });

    window.addEventListener('keyup', (e) => {
      if (e.code === 'Space') {
        this.spacePressed = false;
        this.container.style.cursor = '';
      }
    });

    // Mouse wheel zoom
    this.container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = 1.1;
      const rect = this.container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      let newScale = e.deltaY < 0 ? this.scale * zoomFactor : this.scale / zoomFactor;
      newScale = Math.min(Math.max(this.minScale, newScale), this.maxScale);

      // Center zoom around mouse
      this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
      this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
      this.scale = newScale;

      this.applyTransform();
    }, { passive: false });

    // Minimap click to pan
    if (this.minimapCanvas) {
      this.minimapCanvas.addEventListener('mousedown', (e) => {
        this.handleMinimapClick(e);
      });
    }
  }

  applyTransform() {
    this.world.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
    if (this.callbacks.onZoomChange) {
      this.callbacks.onZoomChange(Math.round(this.scale * 100));
    }
    this.renderMinimap();
  }

  setZoom(percent) {
    const newScale = Math.min(Math.max(this.minScale, percent / 100), this.maxScale);
    const rect = this.container.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;

    this.panX = cx - (cx - this.panX) * (newScale / this.scale);
    this.panY = cy - (cy - this.panY) * (newScale / this.scale);
    this.scale = newScale;
    this.applyTransform();
  }

  resetView() {
    this.scale = 1;
    this.panX = 80;
    this.panY = 50;
    this.applyTransform();
  }

  fitView() {
    if (this.nodes.length === 0) {
      this.resetView();
      return;
    }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.x);
      minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + 300);
      maxY = Math.max(maxY, n.y + 220);
    });

    const padding = 100;
    const rect = this.container.getBoundingClientRect();
    const width = maxX - minX + padding * 2;
    const height = maxY - minY + padding * 2;

    const scaleX = rect.width / width;
    const scaleY = rect.height / height;
    this.scale = Math.min(Math.max(Math.min(scaleX, scaleY), this.minScale), 1.2);

    this.panX = (rect.width - (maxX + minX) * this.scale) / 2;
    this.panY = (rect.height - (maxY + minY) * this.scale) / 2;
    this.applyTransform();
  }

  // Load Graph Data
  loadGraph(graphData) {
    this.nodes = JSON.parse(JSON.stringify(graphData.nodes || []));
    this.connections = JSON.parse(JSON.stringify(graphData.connections || []));
    this.renderAll();
    this.fitView();
  }

  getGraphData() {
    return {
      nodes: this.nodes,
      connections: this.connections
    };
  }

  setNodeIssues(nodeIssues = {}) {
    this.nodeIssues = nodeIssues;
    this.renderAll();
  }

  renderAll() {
    // Clear DOM nodes inside world (except SVG connections and empty state)
    const existingNodes = this.world.querySelectorAll('.workflow-node');
    existingNodes.forEach(el => el.remove());

    const existingEmpty = this.world.querySelector('.canvas-empty-state');
    if (existingEmpty) existingEmpty.remove();

    if (this.nodes.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.className = 'canvas-empty-state';
      emptyEl.innerHTML = `
        <div class="empty-icon-box">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#D95325" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <h3 class="empty-title">Your workflow canvas is clean</h3>
        <p class="empty-desc">Drag an Agent, Task, or Tool from the left palette, or choose a preset template from the dropdown above.</p>
      `;
      this.world.appendChild(emptyEl);
    } else {
      this.nodes.forEach(node => {
        this.renderNodeElement(node);
      });
    }

    this.renderConnections();
    this.renderMinimap();
  }

  renderNodeElement(node) {
    const el = document.createElement('div');
    el.id = `node-${node.id}`;
    const issues = (this.nodeIssues && this.nodeIssues[node.id]) || [];
    const hasWarning = issues.length > 0;
    const isSelected = this.selectedNodeId === node.id;

    el.className = `workflow-node node-${node.type} ${isSelected ? 'selected' : ''} ${hasWarning ? 'has-warning' : ''}`;
    el.style.left = `${node.x}px`;
    el.style.top = `${node.y}px`;

    let badgeIcon = '';
    let badgeText = node.type.toUpperCase();
    let title = node.name || 'Untitled';
    let subtitle = '';
    let pills = [];

    if (node.type === NODE_TYPES.AGENT) {
      badgeIcon = '🤖';
      title = node.role || node.name;
      subtitle = node.goal;
      const isOllama = (node.model_name || '').startsWith('ollama/');
      pills.push(`<span class="pill-badge ${isOllama ? 'ollama-pill' : 'model-pill'}">${node.model_name || 'gpt-4o'}</span>`);
      pills.push(`<span>🌡️ ${node.temperature ?? 0.7}</span>`);
      pills.push(`<span>🔁 ${node.max_iter || 25} max</span>`);
      if (node.allow_delegation) pills.push('<span class="feature-pill">Delegation</span>');
    } else if (node.type === NODE_TYPES.TASK) {
      badgeIcon = '⚡';
      title = node.title || node.name;
      subtitle = node.description;
      if (node.async_execution) pills.push('<span class="feature-pill">⚡ Async</span>');
      if (node.human_input) pills.push('<span class="feature-pill">👤 Human Input</span>');
      if (node.output_file) pills.push(`<span class="file-pill">📄 ${node.output_file}</span>`);
    } else if (node.type === NODE_TYPES.TOOL) {
      badgeIcon = '🛠️';
      title = node.name;
      subtitle = node.tool_type;
      if (node.api_key_env) pills.push(`<span class="key-pill">🔑 ${node.api_key_env}</span>`);
    } else if (node.type === NODE_TYPES.CREW) {
      badgeIcon = '👥';
      title = node.name;
      subtitle = `Process: ${node.process.toUpperCase()}`;
      pills.push(`<span>Verbose: ${node.verbose}</span>`);
      pills.push(`<span>RPM: ${node.max_rpm || 100}</span>`);
      if (node.memory) pills.push('<span class="feature-pill">Memory: On</span>');
    }

    const pillsHtml = pills.map(p => `<span class="node-pill">${p}</span>`).join('');

    // Inline Warning Banners for Error Boundaries
    let warningBannerHtml = '';
    if (issues.length > 0) {
      warningBannerHtml = issues.map(issue => `
        <div class="node-warning-banner">
          <span class="warning-icon">⚠️</span>
          <span class="warning-text">${issue.message}</span>
          ${issue.fixAction ? `<button class="node-fix-btn" data-type="${issue.fixAction.type}" data-target="${issue.fixAction.target}" title="Quick Fix">${issue.fixAction.label} &rarr;</button>` : ''}
        </div>
      `).join('');
    }

    // Determine ports
    let portsHtml = '';
    if (node.type === NODE_TYPES.TOOL) {
      portsHtml = `
        <div class="port port-tool port-output" data-port="output" data-type="tool" data-tooltip="Attach to Agent"></div>
      `;
    } else if (node.type === NODE_TYPES.AGENT) {
      portsHtml = `
        <div class="port port-tool port-input" data-port="input" data-type="tool" data-tooltip="Accept Tools"></div>
        <div class="port port-agent port-output" data-port="output" data-type="agent" data-tooltip="Assign to Task"></div>
      `;
    } else if (node.type === NODE_TYPES.TASK) {
      portsHtml = `
        <div class="port port-agent port-input" data-port="input" data-type="agent" data-tooltip="Assigned Agent / Dependency"></div>
        <div class="port port-task port-output" data-port="output" data-type="task" data-tooltip="Next Task Flow"></div>
      `;
    }

    el.innerHTML = `
      <div class="node-header">
        <span class="node-badge">${badgeIcon} ${badgeText}</span>
        <div class="node-actions">
          <button class="node-btn edit" title="Edit Properties">✏️</button>
          <button class="node-btn clone" title="Duplicate">📋</button>
          <button class="node-btn delete" title="Delete">🗑️</button>
        </div>
      </div>
      <div class="node-body">
        <div class="node-title">${title}</div>
        <div class="node-subtitle">${subtitle || ''}</div>
        ${warningBannerHtml}
        <div class="node-pills">${pillsHtml}</div>
      </div>
      <div class="node-ports">${portsHtml}</div>
    `;

    // Fix button click handler
    el.querySelectorAll('.node-fix-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const type = btn.dataset.type;
        const target = btn.dataset.target;
        if (this.callbacks.onFixIssue) {
          this.callbacks.onFixIssue({ type, target });
        }
      });
    });

    // Events on Node
    el.addEventListener('mousedown', (e) => {
      if (e.target.closest('.node-btn') || e.target.classList.contains('port')) return;
      this.selectNode(node.id);
      this.draggedNode = node;
      this.dragOffset = {
        x: this.mouseWorldPos.x - node.x,
        y: this.mouseWorldPos.y - node.y
      };
      e.stopPropagation();
    });

    // Button actions
    const editBtn = el.querySelector('.node-btn.edit');
    if (editBtn) {
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectNode(node.id, true);
      });
    }

    const cloneBtn = el.querySelector('.node-btn.clone');
    if (cloneBtn) {
      cloneBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.duplicateNode(node.id);
      });
    }

    const delBtn = el.querySelector('.node-btn.delete');
    if (delBtn) {
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeNode(node.id);
      });
    }

    // Port connecting events
    const outputPort = el.querySelector('.port-output');
    if (outputPort) {
      outputPort.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        this.startConnecting(node.id, outputPort.dataset.type, 'output', outputPort);
      });
    }

    const inputPort = el.querySelector('.port-input');
    if (inputPort) {
      inputPort.addEventListener('mouseup', (e) => {
        e.stopPropagation();
        if (this.connecting) {
          this.completeConnection(node.id, inputPort.dataset.type);
        }
      });
    }

    this.world.appendChild(el);
  }

  updateNodePosition(node) {
    const el = document.getElementById(`node-${node.id}`);
    if (el) {
      el.style.left = `${node.x}px`;
      el.style.top = `${node.y}px`;
    }
  }

  selectNode(nodeId, openInspector = false) {
    this.selectedNodeId = nodeId;
    const all = this.world.querySelectorAll('.workflow-node');
    all.forEach(el => el.classList.remove('selected'));

    const el = document.getElementById(`node-${nodeId}`);
    if (el) el.classList.add('selected');

    const node = this.nodes.find(n => n.id === nodeId);
    if (this.callbacks.onSelectNode) {
      this.callbacks.onSelectNode(node, openInspector);
    }
  }

  addNode(node) {
    this.nodes.push(node);
    this.renderNodeElement(node);
    this.selectNode(node.id, true);
    this.renderMinimap();
    if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
  }

  removeNode(nodeId) {
    this.nodes = this.nodes.filter(n => n.id !== nodeId);
    this.connections = this.connections.filter(c => c.sourceId !== nodeId && c.targetId !== nodeId);

    const el = document.getElementById(`node-${nodeId}`);
    if (el) el.remove();

    if (this.selectedNodeId === nodeId) {
      this.selectedNodeId = null;
      if (this.callbacks.onSelectNode) this.callbacks.onSelectNode(null);
    }

    this.renderConnections();
    this.renderMinimap();
    if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
  }

  duplicateNode(nodeId) {
    const original = this.nodes.find(n => n.id === nodeId);
    if (!original) return;
    const clone = JSON.parse(JSON.stringify(original));
    clone.id = `${clone.type}_${Date.now().toString(36)}_${Math.random().toString(36).substr(2, 4)}`;
    clone.x += 40;
    clone.y += 40;
    clone.name = `${original.name}_Copy`;
    this.addNode(clone);
  }

  updateNodeData(nodeId, updatedFields) {
    const node = this.nodes.find(n => n.id === nodeId);
    if (!node) return;
    Object.assign(node, updatedFields);
    // Re-render this node's DOM
    const oldEl = document.getElementById(`node-${nodeId}`);
    if (oldEl) oldEl.remove();
    this.renderNodeElement(node);
    this.renderConnections();
    this.renderMinimap();
    if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
  }

  // Connecting Logic
  startConnecting(nodeId, portType, portDir, element) {
    this.connecting = true;
    this.connectSource = { nodeId, portType, portDir, element };
    this.container.classList.add('connecting');

    // Create preview path in SVG
    if (!this.previewPath) {
      this.previewPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      this.previewPath.setAttribute('class', 'connection-path preview-path');
      this.svg.appendChild(this.previewPath);
    }
  }

  updatePreviewPath() {
    const srcPortPos = this.getPortWorldPosition(this.connectSource.nodeId, 'output');
    if (!srcPortPos) return;

    const startX = srcPortPos.x;
    const startY = srcPortPos.y;
    const endX = this.mouseWorldPos.x;
    const endY = this.mouseWorldPos.y;

    const dx = Math.abs(endX - startX) * 0.5;
    const d = `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`;
    this.previewPath.setAttribute('d', d);
  }

  completeConnection(targetNodeId, targetPortType) {
    if (!this.connecting || !this.connectSource) return;
    const sourceNodeId = this.connectSource.nodeId;
    const sourceType = this.connectSource.portType;

    if (sourceNodeId === targetNodeId) {
      this.cancelConnecting();
      return;
    }

    const sourceNode = this.nodes.find(n => n.id === sourceNodeId);
    const targetNode = this.nodes.find(n => n.id === targetNodeId);
    if (!sourceNode || !targetNode) {
      this.cancelConnecting();
      return;
    }

    // Determine connection kind
    let connType = null;
    if (sourceNode.type === NODE_TYPES.TOOL && targetNode.type === NODE_TYPES.AGENT) {
      connType = 'tool-agent';
    } else if (sourceNode.type === NODE_TYPES.AGENT && targetNode.type === NODE_TYPES.TASK) {
      connType = 'agent-task';
    } else if (sourceNode.type === NODE_TYPES.TASK && targetNode.type === NODE_TYPES.TASK) {
      connType = 'task-task';
    }

    if (connType) {
      // Check if duplicate
      const exists = this.connections.some(c => c.sourceId === sourceNodeId && c.targetId === targetNodeId);
      if (!exists) {
        this.connections.push({
          id: `conn_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
          type: connType,
          sourceId: sourceNodeId,
          targetId: targetNodeId
        });
        this.renderConnections();
        if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
        if (this.callbacks.onNotify) this.callbacks.onNotify(`Connected ${sourceNode.name} to ${targetNode.name}`, 'success');
      }
    }

    this.cancelConnecting();
  }

  endConnecting(e) {
    if (!this.connecting) return;
    this.cancelConnecting();
  }

  cancelConnecting() {
    this.connecting = false;
    this.connectSource = null;
    this.container.classList.remove('connecting');
    if (this.previewPath) {
      this.previewPath.remove();
      this.previewPath = null;
    }
  }

  getPortWorldPosition(nodeId, dir = 'output') {
    const el = document.getElementById(`node-${nodeId}`);
    if (!el) return null;
    const node = this.nodes.find(n => n.id === nodeId);
    if (!node) return null;

    const width = el.offsetWidth || 280;
    const height = el.offsetHeight || 160;

    return {
      x: dir === 'output' ? node.x + width : node.x,
      y: node.y + (height / 2)
    };
  }

  renderConnections() {
    // Clear existing paths
    const paths = this.svg.querySelectorAll('.connection-path:not(.preview-path)');
    paths.forEach(p => p.remove());

    this.connections.forEach(conn => {
      const srcPos = this.getPortWorldPosition(conn.sourceId, 'output');
      const dstPos = this.getPortWorldPosition(conn.targetId, 'input');
      if (!srcPos || !dstPos) return;

      const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      pathEl.setAttribute('class', `connection-path ${conn.type}`);
      pathEl.setAttribute('id', conn.id);

      const dx = Math.max(Math.abs(dstPos.x - srcPos.x) * 0.5, 40);
      const d = `M ${srcPos.x} ${srcPos.y} C ${srcPos.x + dx} ${srcPos.y}, ${dstPos.x - dx} ${dstPos.y}, ${dstPos.x} ${dstPos.y}`;
      pathEl.setAttribute('d', d);

      // Click to disconnect
      pathEl.addEventListener('click', (e) => {
        e.stopPropagation();
        if (confirm('Disconnect this connection?')) {
          this.removeConnection(conn.id);
        }
      });

      this.svg.appendChild(pathEl);
    });
  }

  removeConnection(connId) {
    this.connections = this.connections.filter(c => c.id !== connId);
    this.renderConnections();
    if (this.callbacks.onGraphChanged) this.callbacks.onGraphChanged();
  }

  // Minimap
  renderMinimap() {
    if (!this.minimapCtx) return;
    const ctx = this.minimapCtx;
    const w = this.minimapCanvas.width = 180;
    const h = this.minimapCanvas.height = 120;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#FAF9F5';
    ctx.fillRect(0, 0, w, h);

    if (this.nodes.length === 0) return;

    // Find bounding box
    let minX = 0, minY = 0, maxX = 1600, maxY = 1000;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.x - 100);
      minY = Math.min(minY, n.y - 100);
      maxX = Math.max(maxX, n.x + 400);
      maxY = Math.max(maxY, n.y + 300);
    });

    const worldW = maxX - minX;
    const worldH = maxY - minY;
    const mapScale = Math.min(w / worldW, h / worldH);

    // Draw nodes on minimap using warm minimalist palette
    this.nodes.forEach(n => {
      const nx = (n.x - minX) * mapScale;
      const ny = (n.y - minY) * mapScale;
      const nw = 280 * mapScale;
      const nh = 140 * mapScale;

      if (n.type === NODE_TYPES.AGENT) ctx.fillStyle = '#2D6A4F';      // Sage Green
      else if (n.type === NODE_TYPES.TASK) ctx.fillStyle = '#B45309';  // Warm Amber
      else if (n.type === NODE_TYPES.TOOL) ctx.fillStyle = '#334155';  // Slate Blue-Gray
      else ctx.fillStyle = '#D95325';                                 // Terracotta

      ctx.fillRect(nx, ny, Math.max(nw, 4), Math.max(nh, 3));
    });

    // Draw camera viewport rect in warm terracotta
    const vpLeft = (-this.panX / this.scale - minX) * mapScale;
    const vpTop = (-this.panY / this.scale - minY) * mapScale;
    const vpW = (this.container.clientWidth / this.scale) * mapScale;
    const vpH = (this.container.clientHeight / this.scale) * mapScale;

    ctx.strokeStyle = '#D95325';
    ctx.lineWidth = 1.5;
    ctx.fillStyle = 'rgba(217, 83, 37, 0.08)';
    ctx.fillRect(vpLeft, vpTop, vpW, vpH);
    ctx.strokeRect(vpLeft, vpTop, vpW, vpH);
  }

  handleMinimapClick(e) {
    const rect = this.minimapCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    let minX = 0, minY = 0, maxX = 1600, maxY = 1000;
    this.nodes.forEach(n => {
      minX = Math.min(minX, n.x - 100);
      minY = Math.min(minY, n.y - 100);
      maxX = Math.max(maxX, n.x + 400);
      maxY = Math.max(maxY, n.y + 300);
    });

    const worldW = maxX - minX;
    const worldH = maxY - minY;
    const mapScale = Math.min(180 / worldW, 120 / worldH);

    const targetWorldX = minX + (clickX / mapScale);
    const targetWorldY = minY + (clickY / mapScale);

    this.panX = (this.container.clientWidth / 2) - targetWorldX * this.scale;
    this.panY = (this.container.clientHeight / 2) - targetWorldY * this.scale;
    this.applyTransform();
  }
}
