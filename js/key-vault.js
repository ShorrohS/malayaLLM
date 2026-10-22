/**
 * Visual CrewAI Agent & Workflow Builder
 * Professional Operations Center - Live API Key Vault & Local Ollama Model Discovery
 */

import { LLM_MODELS } from './nodes.js';

export const CLOUD_PROVIDERS = [
  {
    id: 'groq',
    envKey: 'GROQ_API_KEY',
    name: 'Groq Cloud (Llama 3.3)',
    icon: '🚀',
    placeholder: 'gsk_... (Enter multiple keys separated by commas)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().startsWith('gsk_') && k.trim().length >= 25),
    docsUrl: 'https://console.groq.com/keys'
  },
  {
    id: 'gemini',
    envKey: 'GEMINI_API_KEY',
    name: 'Google Gemini 2.0 / 1.5',
    icon: '✨',
    placeholder: 'AIzaSy... (Enter multiple keys separated by commas)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().length >= 25),
    docsUrl: 'https://aistudio.google.com/app/apikey'
  },
  {
    id: 'openrouter',
    envKey: 'OPENROUTER_API_KEY',
    name: 'OpenRouter (Multi-LLM)',
    icon: '🌐',
    placeholder: 'sk-or-v1-... (Enter multiple keys separated by commas)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().startsWith('sk-or-') && k.trim().length >= 25),
    docsUrl: 'https://openrouter.ai/keys'
  },
  {
    id: 'nvidia',
    envKey: 'NVIDIA_API_KEY',
    name: 'NVIDIA NIM (Nemotron)',
    icon: '🟢',
    placeholder: 'nvapi-... (Enter multiple keys separated by commas)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().length >= 20),
    docsUrl: 'https://build.nvidia.com/'
  },
  {
    id: 'cohere',
    envKey: 'COHERE_API_KEY',
    name: 'Cohere (Command R+)',
    icon: '🔮',
    placeholder: 'Cohere API Key... (Enter multiple keys)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().length >= 20),
    docsUrl: 'https://dashboard.cohere.com/api-keys'
  },
  {
    id: 'openai',
    envKey: 'OPENAI_API_KEY',
    name: 'OpenAI API',
    icon: '⚡',
    placeholder: 'sk-proj-... (Enter multiple keys separated by commas)',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().startsWith('sk-') && k.trim().length >= 25),
    docsUrl: 'https://platform.openai.com/api-keys'
  },
  {
    id: 'anthropic',
    envKey: 'ANTHROPIC_API_KEY',
    name: 'Anthropic Claude',
    icon: '🧠',
    placeholder: 'sk-ant-api03-...',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().startsWith('sk-ant-') && k.trim().length >= 25),
    docsUrl: 'https://console.anthropic.com/settings/keys'
  },
  {
    id: 'serper',
    envKey: 'SERPER_API_KEY',
    name: 'SerperDev Google Search',
    icon: '🔍',
    placeholder: 'Enter Serper API key(s)...',
    validate: (key) => key && key.split(/[\n,;]+/).some(k => k.trim().length >= 20),
    docsUrl: 'https://serper.dev/api-key'
  }
];

export class KeyVault {
  constructor(callbacks = {}) {
    this.callbacks = callbacks; // onKeysUpdated, onOllamaUpdated, onNotify
    this.keys = this.loadStoredKeys();
    this.ollamaStatus = {
      online: false,
      endpoint: 'http://localhost:11434',
      models: [],
      lastChecked: null,
      error: null
    };

    // Auto-discover Ollama models on startup
    this.autoFetchOllamaModels();
  }

  loadStoredKeys() {
    try {
      const stored = localStorage.getItem('crewai_vault_keys');
      if (stored) return JSON.parse(stored);
    } catch (e) {
      console.warn('Failed to load keys from localStorage:', e);
    }
    return {
      GROQ_API_KEY: '',
      GEMINI_API_KEY: '',
      OPENROUTER_API_KEY: '',
      NVIDIA_API_KEY: '',
      COHERE_API_KEY: '',
      OPENAI_API_KEY: '',
      ANTHROPIC_API_KEY: '',
      SERPER_API_KEY: ''
    };
  }

  saveKeys(newKeys) {
    this.keys = { ...this.keys, ...newKeys };
    try {
      localStorage.setItem('crewai_vault_keys', JSON.stringify(this.keys));
    } catch (e) {
      console.warn('Failed to save keys to localStorage:', e);
    }
    if (this.callbacks.onKeysUpdated) {
      this.callbacks.onKeysUpdated(this.keys);
    }
  }

  getKey(envKey) {
    const list = this.getKeyList(envKey);
    return list.length > 0 ? list[0] : '';
  }

  getKeyList(envKey) {
    const raw = this.keys[envKey] || '';
    return raw.split(/[\n,;]+/).map(k => k.trim()).filter(Boolean);
  }

  hasKey(envKey) {
    const list = this.getKeyList(envKey);
    return list.length > 0;
  }

  getActiveKeyCount() {
    return CLOUD_PROVIDERS.filter(p => this.hasKey(p.envKey)).length;
  }

  getTotalKeyCount() {
    return CLOUD_PROVIDERS.reduce((total, p) => total + this.getKeyList(p.envKey).length, 0);
  }

  async autoFetchOllamaModels() {
    this.ollamaStatus.lastChecked = new Date();
    try {
      // First try local server proxy endpoint
      let resp = await fetch('/api/ollama/tags', { cache: 'no-store' });
      if (!resp.ok) {
        // Fallback to direct fetch
        resp = await fetch('http://localhost:11434/api/tags', { cache: 'no-store' });
      }

      const data = await resp.json();
      if (data.models && Array.isArray(data.models) && data.models.length > 0) {
        this.ollamaStatus.online = true;
        this.ollamaStatus.models = data.models;
        this.ollamaStatus.error = null;

        // Dynamically populate discovered models into LLM_MODELS catalog
        this.registerOllamaModelsInCatalog(data.models);
      } else if (data.status === 'offline') {
        this.ollamaStatus.online = false;
        this.ollamaStatus.error = data.error || 'Daemon offline';
        this.ollamaStatus.models = [];
      } else {
        this.ollamaStatus.online = true;
        this.ollamaStatus.models = [];
        this.ollamaStatus.error = 'No models pulled yet (run: ollama pull llama3.2)';
      }
    } catch (err) {
      this.ollamaStatus.online = false;
      this.ollamaStatus.error = 'Could not reach http://localhost:11434';
      this.ollamaStatus.models = [];
    }

    if (this.callbacks.onOllamaUpdated) {
      this.callbacks.onOllamaUpdated(this.ollamaStatus);
    }
    return this.ollamaStatus;
  }

  registerOllamaModelsInCatalog(modelsList) {
    const dynamicModels = modelsList.map(m => {
      const sizeGB = (m.size / (1024 * 1024 * 1024)).toFixed(1);
      return {
        id: `ollama/${m.name}`,
        name: `${m.name} (${sizeGB} GB - Local)`,
        keyEnv: null,
        isDiscovered: true
      };
    });

    // Add fallback defaults if not already present
    const defaultFallbacks = [
      { id: 'ollama/llama3.2:latest', name: 'Llama 3.2 (Local Ollama)', keyEnv: null },
      { id: 'ollama/mistral:latest', name: 'Mistral 7B (Local Ollama)', keyEnv: null },
      { id: 'ollama/qwen2.5:latest', name: 'Qwen 2.5 (Local Ollama)', keyEnv: null },
      { id: 'ollama/deepseek-r1:latest', name: 'DeepSeek R1 (Local Ollama)', keyEnv: null }
    ];

    // Combine discovered models at top, followed by other popular defaults
    const combined = [...dynamicModels];
    defaultFallbacks.forEach(def => {
      if (!combined.some(c => c.id === def.id)) {
        combined.push(def);
      }
    });

    LLM_MODELS['Ollama (Local Offline)'] = combined;
  }
}
