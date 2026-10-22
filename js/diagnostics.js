/**
 * Visual CrewAI Agent & Workflow Builder
 * Professional Operations Center - Network & Topology Diagnostics Engine
 */

import { NODE_TYPES, LLM_MODELS, TOOL_DEFINITIONS } from './nodes.js';

export class DiagnosticsManager {
  constructor(callbacks = {}) {
    this.callbacks = callbacks; // onFixIssue, onOpenKeyVault, onSelectNode
    this.lastReport = null;
  }

  auditWorkflow(graph, keyVault) {
    const { nodes = [], connections = [] } = graph;
    const checks = [];
    const warnings = [];
    const errors = [];
    const nodeIssues = {}; // nodeId -> array of issue messages

    const addNodeIssue = (nodeId, severity, message, fixAction) => {
      if (!nodeIssues[nodeId]) nodeIssues[nodeId] = [];
      nodeIssues[nodeId].push({ severity, message, fixAction });
      if (severity === 'error') errors.push({ nodeId, message, fixAction });
      else warnings.push({ nodeId, message, fixAction });
    };

    const agents = nodes.filter(n => n.type === NODE_TYPES.AGENT);
    const tasks = nodes.filter(n => n.type === NODE_TYPES.TASK);
    const tools = nodes.filter(n => n.type === NODE_TYPES.TOOL);
    const crew = nodes.find(n => n.type === NODE_TYPES.CREW);

    // 1. Check Agents & Required Cloud API Keys / Ollama models
    agents.forEach(agent => {
      const model = agent.model_name || 'gpt-4o';
      const isOllama = model.startsWith('ollama/');

      if (isOllama) {
        if (!keyVault.ollamaStatus.online) {
          addNodeIssue(agent.id, 'warning', `Ollama daemon offline (model: ${model})`, {
            type: 'open_vault',
            target: 'ollama',
            label: 'Check Ollama Status'
          });
        }
      } else {
        // Find required env key
        let requiredKey = 'OPENAI_API_KEY';
        for (const [provider, models] of Object.entries(LLM_MODELS)) {
          const found = models.find(m => m.id === model);
          if (found && found.keyEnv) requiredKey = found.keyEnv;
        }

        if (!keyVault.hasKey(requiredKey)) {
          addNodeIssue(agent.id, 'warning', `Missing required ${requiredKey}`, {
            type: 'open_vault',
            target: requiredKey,
            label: `Add ${requiredKey}`
          });
        }
      }
    });

    // 2. Check Tasks: Must have assigned agent
    tasks.forEach(task => {
      const hasDirectAgent = !!task.agent_id && agents.some(a => a.id === task.agent_id);
      const hasConnectedAgent = connections.some(c => 
        c.type === 'agent-task' && (c.targetId === task.id || c.sourceId === task.id)
      );

      if (!hasDirectAgent && !hasConnectedAgent) {
        addNodeIssue(task.id, 'warning', 'No Agent assigned to this task', {
          type: 'select_node',
          target: task.id,
          label: 'Assign Agent'
        });
      }
    });

    // 3. Check Tools: If requires key (e.g. SERPER_API_KEY)
    tools.forEach(tool => {
      const def = TOOL_DEFINITIONS[tool.tool_type];
      const reqKey = tool.api_key_env || (def ? def.reqKey : null);
      if (reqKey && !keyVault.hasKey(reqKey)) {
        addNodeIssue(tool.id, 'warning', `Missing ${reqKey}`, {
          type: 'open_vault',
          target: reqKey,
          label: `Configure ${reqKey}`
        });
      }

      // Check if attached to any agent
      const isAttached = connections.some(c => 
        c.type === 'tool-agent' && (c.sourceId === tool.id || c.targetId === tool.id)
      );
      if (!isAttached) {
        addNodeIssue(tool.id, 'info', 'Tool is unattached to any Agent', {
          type: 'select_node',
          target: tool.id,
          label: 'Connect to Agent'
        });
      }
    });

    // 4. Check Crew Configuration
    if (crew && crew.process === 'hierarchical') {
      if (!crew.manager_llm) {
        addNodeIssue(crew.id, 'error', 'Hierarchical crew requires a Manager LLM', {
          type: 'select_node',
          target: crew.id,
          label: 'Set Manager LLM'
        });
      }
      if (!keyVault.hasKey('OPENAI_API_KEY')) {
        addNodeIssue(crew.id, 'warning', 'Hierarchical manager recommends OPENAI_API_KEY', {
          type: 'open_vault',
          target: 'OPENAI_API_KEY',
          label: 'Add OPENAI_API_KEY'
        });
      }
    }

    // Overall Status
    let status = 'healthy';
    if (errors.length > 0) status = 'error';
    else if (warnings.length > 0) status = 'warning';

    this.lastReport = {
      status,
      timestamp: new Date(),
      totalNodes: nodes.length,
      totalConnections: connections.length,
      agentCount: agents.length,
      taskCount: tasks.length,
      toolCount: tools.length,
      errors,
      warnings,
      nodeIssues,
      ollamaStatus: keyVault.ollamaStatus
    };

    return this.lastReport;
  }
}
