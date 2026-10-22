/**
 * Visual CrewAI Agent & Workflow Builder
 * Node Definitions, Data Models & Schema Helpers
 */

export const NODE_TYPES = {
  AGENT: 'agent',
  TASK: 'task',
  TOOL: 'tool',
  CREW: 'crew'
};

export const LLM_MODELS = {
  'Groq (Ultra-Fast Llama)': [
    { id: 'groq/llama-3.3-70b-versatile', name: 'Llama 3.3 70B (Groq)', keyEnv: 'GROQ_API_KEY' },
    { id: 'groq/llama-3.1-8b-instant', name: 'Llama 3.1 8B Instant (Groq)', keyEnv: 'GROQ_API_KEY' }
  ],
  'Google Gemini': [
    { id: 'gemini/gemini-2.0-flash', name: 'Gemini 2.0 Flash (Fast & SOTA)', keyEnv: 'GEMINI_API_KEY' },
    { id: 'gemini/gemini-1.5-pro', name: 'Gemini 1.5 Pro (2M context)', keyEnv: 'GEMINI_API_KEY' },
    { id: 'gemini/gemini-1.5-flash', name: 'Gemini 1.5 Flash (Efficient)', keyEnv: 'GEMINI_API_KEY' }
  ],
  'OpenRouter (Multi-LLM)': [
    { id: 'openrouter/meta-llama/llama-3.3-70b-instruct:free', name: 'Llama 3.3 70B (Free Tier)', keyEnv: 'OPENROUTER_API_KEY' },
    { id: 'openrouter/google/gemini-2.0-flash-exp:free', name: 'Gemini 2.0 Flash (Free Tier)', keyEnv: 'OPENROUTER_API_KEY' },
    { id: 'openrouter/auto', name: 'Auto Best Router', keyEnv: 'OPENROUTER_API_KEY' }
  ],
  'NVIDIA NIM': [
    { id: 'nvidia/meta/llama-3.1-70b-instruct', name: 'Llama 3.1 70B (NVIDIA NIM)', keyEnv: 'NVIDIA_API_KEY' },
    { id: 'nvidia/nvidia/llama-3.1-nemotron-70b-instruct', name: 'Nemotron 70B (NVIDIA NIM)', keyEnv: 'NVIDIA_API_KEY' }
  ],
  'Cohere (Multi-Lingual)': [
    { id: 'cohere/command-r-plus', name: 'Command R+ (Indic/Malayalam)', keyEnv: 'COHERE_API_KEY' },
    { id: 'cohere/command-r', name: 'Command R', keyEnv: 'COHERE_API_KEY' }
  ],
  'OpenAI': [
    { id: 'gpt-4o', name: 'GPT-4o (Omni flagship)', keyEnv: 'OPENAI_API_KEY' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini (Fast & cheap)', keyEnv: 'OPENAI_API_KEY' },
    { id: 'o1-preview', name: 'OpenAI o1 Preview (Reasoning)', keyEnv: 'OPENAI_API_KEY' },
    { id: 'o1-mini', name: 'OpenAI o1 Mini (Fast reasoning)', keyEnv: 'OPENAI_API_KEY' }
  ],
  'Anthropic': [
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet (State of the art)', keyEnv: 'ANTHROPIC_API_KEY' },
    { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku (Ultra fast)', keyEnv: 'ANTHROPIC_API_KEY' },
    { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus (Deep thinking)', keyEnv: 'ANTHROPIC_API_KEY' }
  ],
  'Ollama (Local Offline)': [
    { id: 'ollama/llama3.2:latest', name: 'Llama 3.2 (Local Ollama)', keyEnv: null },
    { id: 'ollama/mistral:latest', name: 'Mistral 7B (Local Ollama)', keyEnv: null },
    { id: 'ollama/qwen2.5:latest', name: 'Qwen 2.5 (Local Ollama)', keyEnv: null },
    { id: 'ollama/deepseek-r1:latest', name: 'DeepSeek R1 (Local Ollama)', keyEnv: null }
  ]
};

export const TOOL_DEFINITIONS = {
  'MalayalamWebCrawlerTool': {
    name: 'Malayalam Web & Archive Crawler',
    importStmt: 'from crewai_tools import ScrapeWebsiteTool',
    instanceCode: 'MalayalamWebCrawlerTool()',
    reqKey: null,
    desc: 'Targeted crawler for Malayalam regional news (Mathrubhumi/Manorama), Wikipedia, and CommonCrawl.'
  },
  'MalayalamUnicodeCleanerTool': {
    name: 'Malayalam Morphological Cleaner',
    importStmt: 'from utils.malayalam_cleaner import MalayalamCleaner',
    instanceCode: 'MalayalamUnicodeCleanerTool()',
    reqKey: null,
    desc: 'NFKC normalization, atomic Chillu standardization (ൺ,ൻ,ർ,ൽ,ൾ,ൿ), PII redaction, >=60% density check.'
  },
  'MalayalamFluencyCriticTool': {
    name: 'LLM-as-a-Judge Quality Critic',
    importStmt: 'from utils.malayalam_cleaner import MalayalamCleaner',
    instanceCode: 'MalayalamFluencyCriticTool()',
    reqKey: null,
    desc: 'Morphological quality scorer, agglutination validator, and translationese artifact detector.'
  },
  'SerperDevTool': {
    name: 'Google Search (Serper)',
    importStmt: 'from crewai_tools import SerperDevTool',
    instanceCode: 'SerperDevTool()',
    reqKey: 'SERPER_API_KEY',
    desc: 'Perform real-time Google searches to gather current web results.'
  },
  'ScrapeWebsiteTool': {
    name: 'Website Scraper',
    importStmt: 'from crewai_tools import ScrapeWebsiteTool',
    instanceCode: 'ScrapeWebsiteTool()',
    reqKey: null,
    desc: 'Extract full markdown or HTML content from any given URL.'
  },
  'DirectoryReadTool': {
    name: 'Directory Reader',
    importStmt: 'from crewai_tools import DirectoryReadTool',
    instanceCode: 'DirectoryReadTool()',
    reqKey: null,
    desc: 'Browse and recursively read contents of a local folder.'
  },
  'FileReadTool': {
    name: 'File Reader',
    importStmt: 'from crewai_tools import FileReadTool',
    instanceCode: 'FileReadTool()',
    reqKey: null,
    desc: 'Read and parse text/code/markdown files on disk.'
  },
  'CSVSearchTool': {
    name: 'CSV RAG Search Tool',
    importStmt: 'from crewai_tools import CSVSearchTool',
    instanceCode: 'CSVSearchTool()',
    reqKey: 'OPENAI_API_KEY',
    desc: 'Semantic vector search inside structured tabular CSV files.'
  },
  'WebsiteSearchTool': {
    name: 'RAG Web Document Search',
    importStmt: 'from crewai_tools import WebsiteSearchTool',
    instanceCode: 'WebsiteSearchTool()',
    reqKey: 'OPENAI_API_KEY',
    desc: 'Perform vector search queries on specific target web pages.'
  },
  'CustomPythonTool': {
    name: 'Custom Python Tool',
    importStmt: 'from crewai.tools import tool',
    instanceCode: 'custom_execution_tool',
    reqKey: null,
    desc: 'Execute custom python functions decorated with @tool.'
  }
};

let nextIdCounter = 1;

export function generateId(prefix = 'node') {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).substr(2, 4)}`;
}

export function createDefaultAgent(x = 100, y = 100, customProps = {}) {
  const count = customProps.index || nextIdCounter++;
  return {
    id: generateId('agent'),
    type: NODE_TYPES.AGENT,
    x,
    y,
    name: `Agent_${count}`,
    role: 'Senior Research Analyst',
    goal: 'Uncover cutting-edge developments, synthesize complex data, and produce actionable insights',
    backstory: 'You are a world-class investigative analyst with 15 years of industry experience. Known for precision, relentless fact-checking, and clear summaries.',
    llm_provider: 'OpenAI',
    model_name: 'gpt-4o',
    temperature: 0.7,
    verbose: true,
    allow_delegation: false,
    memory: true,
    max_iter: 25,
    tools: [], // Tool IDs assigned
    ...customProps
  };
}

export function createDefaultTask(x = 450, y = 100, customProps = {}) {
  const count = customProps.index || nextIdCounter++;
  return {
    id: generateId('task'),
    type: NODE_TYPES.TASK,
    x,
    y,
    name: `Task_${count}`,
    title: 'Conduct Deep Industry Analysis',
    description: 'Investigate the latest market trends for 2026. Identify top 3 key breakthroughs, market drivers, and potential competitive risks.',
    expected_output: 'A comprehensive 4-paragraph markdown executive brief with bulleted key findings and strategic recommendations.',
    agent_id: null, // Assigned agent ID
    async_execution: false,
    output_file: 'analysis_report.md',
    human_input: false,
    depends_on: [], // prior task IDs
    ...customProps
  };
}

export function createDefaultTool(x = 100, y = 400, customProps = {}) {
  const toolType = customProps.tool_type || 'SerperDevTool';
  const def = TOOL_DEFINITIONS[toolType] || TOOL_DEFINITIONS['SerperDevTool'];
  return {
    id: generateId('tool'),
    type: NODE_TYPES.TOOL,
    x,
    y,
    tool_type: toolType,
    name: def.name,
    api_key_env: def.reqKey,
    parameters: {},
    custom_code: `@tool("Custom Action Tool")\ndef custom_action(data: str) -> str:\n    """Executes a specialized custom function."""\n    return f"Processed: {data}"\n`,
    ...customProps
  };
}

export function createDefaultCrew(x = 800, y = 100, customProps = {}) {
  return {
    id: generateId('crew'),
    type: NODE_TYPES.CREW,
    x,
    y,
    name: 'AutonomousExecutiveCrew',
    process: 'sequential', // 'sequential' or 'hierarchical'
    manager_llm: 'gpt-4o',
    memory: true,
    verbose: 2,
    cache: true,
    max_rpm: 100,
    share_crew: false,
    ...customProps
  };
}
