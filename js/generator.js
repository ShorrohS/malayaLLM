/**
 * Visual CrewAI Agent & Workflow Builder
 * Real-Time Code Generator for CrewAI Projects
 */

import { TOOL_DEFINITIONS, LLM_MODELS } from './nodes.js';

function sanitizeVarName(name) {
  if (!name) return 'item';
  return name.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '') || 'item';
}

function yamlMultiline(text, indent = 4) {
  if (!text) return ' >\n' + ' '.repeat(indent) + 'None';
  const lines = text.trim().split('\n');
  if (lines.length === 1 && !lines[0].includes(':') && !lines[0].includes('"')) {
    return ` >\n${' '.repeat(indent)}${lines[0]}`;
  }
  return ' >\n' + lines.map(line => `${' '.repeat(indent)}${line}`).join('\n');
}

export function generateCrewProject(graph) {
  const { nodes = [], connections = [] } = graph;

  const agents = nodes.filter(n => n.type === 'agent');
  const tasks = nodes.filter(n => n.type === 'task');
  const tools = nodes.filter(n => n.type === 'tool');
  const crewNode = nodes.find(n => n.type === 'crew') || {
    name: 'AutonomousCrew',
    process: 'sequential',
    manager_llm: 'gpt-4o',
    memory: true,
    verbose: 2,
    cache: true,
    max_rpm: 100
  };

  // Map agent connections
  // Find tool-to-agent connections
  const agentToolsMap = {};
  agents.forEach(a => { agentToolsMap[a.id] = []; });
  connections.forEach(conn => {
    if (conn.type === 'tool-agent') {
      const tool = tools.find(t => t.id === conn.sourceId);
      if (tool && agentToolsMap[conn.targetId]) {
        agentToolsMap[conn.targetId].push(tool);
      }
    }
    // Also support manual tools array on agent
    if (conn.sourceId && conn.targetId) {
      const a = agents.find(ag => ag.id === conn.targetId);
      const t = tools.find(tl => tl.id === conn.sourceId);
      if (a && t && !agentToolsMap[a.id].some(item => item.id === t.id)) {
        agentToolsMap[a.id].push(t);
      }
    }
  });

  // Assign agent for tasks
  const taskAgentMap = {};
  tasks.forEach(task => {
    // Check if task has direct agent_id
    if (task.agent_id) {
      const agent = agents.find(a => a.id === task.agent_id);
      if (agent) taskAgentMap[task.id] = agent;
    }
    // Check connection agent-task
    const conn = connections.find(c => c.type === 'agent-task' && (c.targetId === task.id || c.sourceId === task.id));
    if (conn) {
      const agentId = conn.sourceId === task.id ? conn.targetId : conn.sourceId;
      const agent = agents.find(a => a.id === agentId);
      if (agent) taskAgentMap[task.id] = agent;
    }
  });

  // Detect needed environment keys
  const neededKeys = new Set();
  agents.forEach(a => {
    for (const [provider, models] of Object.entries(LLM_MODELS)) {
      const found = models.find(m => m.id === a.model_name);
      if (found && found.keyEnv) neededKeys.add(found.keyEnv);
    }
  });
  tools.forEach(t => {
    const def = TOOL_DEFINITIONS[t.tool_type];
    if (def && def.reqKey) neededKeys.add(def.reqKey);
  });
  if (crewNode.process === 'hierarchical' && crewNode.manager_llm) {
    neededKeys.add('OPENAI_API_KEY');
  }

  // Generate agents.yaml
  let agentsYaml = `# CrewAI Agent Configuration\n# Generated automatically by Visual CrewAI Agent & Workflow Builder\n\n`;
  agents.forEach(agent => {
    const key = sanitizeVarName(agent.name || agent.role);
    agentsYaml += `${key}:\n`;
    agentsYaml += `  role:${yamlMultiline(agent.role, 4)}\n`;
    agentsYaml += `  goal:${yamlMultiline(agent.goal, 4)}\n`;
    agentsYaml += `  backstory:${yamlMultiline(agent.backstory, 4)}\n\n`;
  });

  // Generate tasks.yaml
  let tasksYaml = `# CrewAI Task Configuration\n# Generated automatically by Visual CrewAI Agent & Workflow Builder\n\n`;
  tasks.forEach(task => {
    const key = sanitizeVarName(task.name || task.title);
    const assignedAgent = taskAgentMap[task.id];
    const agentKey = assignedAgent ? sanitizeVarName(assignedAgent.name || assignedAgent.role) : 'default_agent';

    tasksYaml += `${key}:\n`;
    tasksYaml += `  description:${yamlMultiline(task.description, 4)}\n`;
    tasksYaml += `  expected_output:${yamlMultiline(task.expected_output, 4)}\n`;
    tasksYaml += `  agent: ${agentKey}\n`;
    if (task.output_file) {
      tasksYaml += `  output_file: ${task.output_file}\n`;
    }
    tasksYaml += '\n';
  });

  // Generate crew.py
  const toolImports = new Set();
  const toolInstantiations = [];
  tools.forEach(t => {
    const def = TOOL_DEFINITIONS[t.tool_type];
    if (def) {
      toolImports.add(def.importStmt);
    }
  });

  const crewClassName = sanitizeVarName(crewNode.name || 'AutonomousCrew').replace(/(^|_)([a-z])/g, (_, a, b) => b.toUpperCase());

  let crewPy = `import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
`;
  toolImports.forEach(imp => { crewPy += `${imp}\n`; });

  // Custom tool definitions if any
  const customTools = tools.filter(t => t.tool_type === 'CustomPythonTool');
  if (customTools.length > 0) {
    crewPy += `\n# Custom Tools\n`;
    customTools.forEach(ct => {
      crewPy += `${ct.custom_code || ''}\n`;
    });
  }

  crewPy += `\n@CrewBase
class ${crewClassName}():
    """${crewClassName} orchestrator"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
`;

  // Methods for agents
  agents.forEach(agent => {
    const funcName = sanitizeVarName(agent.name || agent.role);
    const assignedTools = agentToolsMap[agent.id] || [];
    const toolTokens = assignedTools.map(t => {
      const def = TOOL_DEFINITIONS[t.tool_type];
      return def ? def.instanceCode : 'None';
    }).filter(x => x !== 'None').join(', ');

    crewPy += `\n    @agent
    def ${funcName}(self) -> Agent:
        return Agent(
            config=self.agents_config['${funcName}'],
            verbose=${agent.verbose ? 'True' : 'False'},
            allow_delegation=${agent.allow_delegation ? 'True' : 'False'},
            memory=${agent.memory ? 'True' : 'False'},
            max_iter=${agent.max_iter || 25},
            llm="${agent.model_name || 'gpt-4o'}",
            tools=[${toolTokens}]
        )\n`;
  });

  // Methods for tasks
  tasks.forEach(task => {
    const funcName = sanitizeVarName(task.name || task.title);
    const assignedAgent = taskAgentMap[task.id];
    const agentFuncName = assignedAgent ? sanitizeVarName(assignedAgent.name || assignedAgent.role) : 'self.agents[0]';

    crewPy += `\n    @task
    def ${funcName}(self) -> Task:
        return Task(
            config=self.tasks_config['${funcName}'],
            agent=self.${agentFuncName}(),
            async_execution=${task.async_execution ? 'True' : 'False'},
            human_input=${task.human_input ? 'True' : 'False'}${task.output_file ? `,\n            output_file='${task.output_file}'` : ''}
        )\n`;
  });

  // Crew definition
  const isHierarchical = crewNode.process === 'hierarchical';
  crewPy += `\n    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.${isHierarchical ? 'hierarchical' : 'sequential'},
            ${isHierarchical ? `manager_llm="${crewNode.manager_llm || 'gpt-4o'}",\n            ` : ''}verbose=${crewNode.verbose || 2},
            memory=${crewNode.memory ? 'True' : 'False'},
            cache=${crewNode.cache ? 'True' : 'False'},
            max_rpm=${crewNode.max_rpm || 100}
        )\n`;

  // Generate main.py
  const mainPy = `#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from dotenv import load_dotenv
from crew import ${crewClassName}

# Load environment variables (.env)
load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Run the visual workflow crew.
    """
    inputs = {
        'topic': 'Next-Gen Autonomous Agent Orchestration',
        'current_year': str(datetime.now().year)
    }
    
    print("\\n=======================================================")
    print("🚀 Starting CrewAI Execution: ${crewClassName}")
    print("=======================================================\\n")
    
    try:
        result = ${crewClassName}().crew().kickoff(inputs=inputs)
        print("\\n=======================================================")
        print("✅ Crew Execution Succeeded!")
        print("=======================================================\\n")
        print("Summary Result:\\n", result)
        return result
    except Exception as e:
        print(f"❌ Execution encountered an error: {e}")
        raise e

if __name__ == "__main__":
    run()
`;

  // Generate Single-File Executable Script (crew_runner.py)
  let singleRunnerPy = `#!/usr/bin/env python
"""
Standalone Executable CrewAI Script
Generated by Visual CrewAI Agent & Workflow Builder
Execute directly with: python crew_runner.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load local environment keys
load_dotenv()

from crewai import Agent, Task, Crew, Process
`;
  toolImports.forEach(imp => { singleRunnerPy += `${imp}\n`; });

  if (customTools.length > 0) {
    singleRunnerPy += `\n# Custom Tools\n`;
    customTools.forEach(ct => {
      singleRunnerPy += `${ct.custom_code || ''}\n`;
    });
  }

  singleRunnerPy += `\ndef run_standalone_crew():\n    print("🤖 Initializing CrewAI Agents & Workflow...")\n\n`;

  // Initialize tools in single script
  singleRunnerPy += `    # 1. Tools Initialization\n`;
  tools.forEach(t => {
    const varName = sanitizeVarName(t.name || t.tool_type);
    const def = TOOL_DEFINITIONS[t.tool_type];
    if (def) {
      singleRunnerPy += `    tool_${varName} = ${def.instanceCode}\n`;
    }
  });

  // Initialize agents in single script
  singleRunnerPy += `\n    # 2. Agents Initialization\n`;
  agents.forEach(a => {
    const varName = sanitizeVarName(a.name || a.role);
    const assignedTools = agentToolsMap[a.id] || [];
    const toolTokens = assignedTools.map(t => `tool_${sanitizeVarName(t.name || t.tool_type)}`).join(', ');

    singleRunnerPy += `    agent_${varName} = Agent(
        role="${a.role.replace(/"/g, '\\"')}",
        goal="${a.goal.replace(/"/g, '\\"')}",
        backstory="${a.backstory.replace(/"/g, '\\"')}",
        llm="${a.model_name || 'gpt-4o'}",
        tools=[${toolTokens}],
        verbose=${a.verbose ? 'True' : 'False'},
        allow_delegation=${a.allow_delegation ? 'True' : 'False'},
        memory=${a.memory ? 'True' : 'False'},
        max_iter=${a.max_iter || 25}
    )\n\n`;
  });

  // Initialize tasks in single script
  singleRunnerPy += `    # 3. Tasks Initialization\n`;
  tasks.forEach(t => {
    const varName = sanitizeVarName(t.name || t.title);
    const assignedAgent = taskAgentMap[t.id];
    const agentVar = assignedAgent ? `agent_${sanitizeVarName(assignedAgent.name || assignedAgent.role)}` : 'agent_' + sanitizeVarName(agents[0]?.name || 'default');

    singleRunnerPy += `    task_${varName} = Task(
        description="${t.description.replace(/"/g, '\\"')}",
        expected_output="${t.expected_output.replace(/"/g, '\\"')}",
        agent=${agentVar},
        async_execution=${t.async_execution ? 'True' : 'False'},
        human_input=${t.human_input ? 'True' : 'False'}${t.output_file ? `,\n        output_file='${t.output_file}'` : ''}
    )\n\n`;
  });

  // Assemble Crew in single script
  const agentList = agents.map(a => `agent_${sanitizeVarName(a.name || a.role)}`).join(', ');
  const taskList = tasks.map(t => `task_${sanitizeVarName(t.name || t.title)}`).join(', ');

  singleRunnerPy += `    # 4. Crew Orchestration\n`;
  singleRunnerPy += `    crew = Crew(
        agents=[${agentList}],
        tasks=[${taskList}],
        process=Process.${isHierarchical ? 'hierarchical' : 'sequential'},
        ${isHierarchical ? `manager_llm="${crewNode.manager_llm || 'gpt-4o'}",\n        ` : ''}verbose=${crewNode.verbose || 2},
        memory=${crewNode.memory ? 'True' : 'False'},
        cache=${crewNode.cache ? 'True' : 'False'}
    )

    print("🚀 Running Crew Kickoff...")
    result = crew.kickoff()
    print("\\n🎉 Crew Execution Completed Successfully!")
    print("------------------------------------------")
    print(result)
    return result

if __name__ == "__main__":
    run_standalone_crew()
`;

  // Generate .env template
  let envFile = `# Environment Variables for CrewAI Workflow
# Fill in your valid API keys below

`;
  if (neededKeys.size === 0) {
    envFile += `# No cloud API keys required (e.g. running local Ollama)\n`;
  } else {
    neededKeys.forEach(k => {
      const rawVal = customEnvKeys && customEnvKeys[k] ? customEnvKeys[k].trim() : '';
      const actualVal = rawVal || `your_${k.toLowerCase()}_here`;
      envFile += `${k}=${actualVal}\n`;
      // Also export plural format for key_rotator.py if multiple keys provided
      if (rawVal.includes(',') || rawVal.includes(';') || rawVal.includes('\n')) {
        const sanitizedList = rawVal.split(/[\n,;]+/).map(s => s.trim()).filter(Boolean).join(',');
        const pluralKey = k.endsWith('_KEY') ? k.replace('_KEY', '_API_KEYS') : `${k}_KEYS`;
        envFile += `${pluralKey}=${sanitizedList}\n`;
      }
    });
  }
  envFile += `\n# Optional CrewAI & Malayalam Pipeline telemetry toggles\nOTEL_SDK_DISABLED=true\nPYTHONIOENCODING=utf-8\n`;

  // Generate requirements.txt
  let reqs = `crewai>=0.86.0\ncrewai-tools>=0.14.0\npython-dotenv>=1.0.0\n`;
  reqs += `unicodedata2>=15.1.0\ndatasets>=2.18.0\n`;

  if (Array.from(neededKeys).some(k => k.includes('OPENAI'))) {
    reqs += `openai>=1.40.0\n`;
  }
  if (Array.from(neededKeys).some(k => k.includes('ANTHROPIC'))) {
    reqs += `anthropic>=0.34.0\n`;
  }
  if (Array.from(neededKeys).some(k => k.includes('GEMINI'))) {
    reqs += `google-generativeai>=0.7.0\n`;
  }
  if (Array.from(neededKeys).some(k => k.includes('GROQ'))) {
    reqs += `groq>=0.11.0\n`;
  }
  if (Array.from(neededKeys).some(k => k.includes('COHERE'))) {
    reqs += `cohere>=5.0.0\n`;
  }

  return {
    agentsYaml,
    tasksYaml,
    crewPy,
    mainPy,
    singleRunnerPy,
    envFile,
    requirementsTxt: reqs,
    metadata: {
      crewName: crewClassName,
      agentCount: agents.length,
      taskCount: tasks.length,
      toolCount: tools.length,
      neededKeys: Array.from(neededKeys)
    }
  };
}
