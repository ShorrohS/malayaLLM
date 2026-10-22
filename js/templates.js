/**
 * Visual CrewAI Agent & Workflow Builder
 * Curated Pre-Built Production Templates
 */

import { NODE_TYPES } from './nodes.js';

export const WORKFLOW_TEMPLATES = {
  market_research: {
    id: 'market_research',
    name: 'Market Research & Competitive Intelligence',
    description: 'Autonomous web research, data extraction, and executive synthesis into a published Markdown brief.',
    nodes: [
      {
        id: 'tool_serper',
        type: NODE_TYPES.TOOL,
        x: 60,
        y: 120,
        tool_type: 'SerperDevTool',
        name: 'Google Search (Serper)',
        api_key_env: 'SERPER_API_KEY'
      },
      {
        id: 'tool_scrape',
        type: NODE_TYPES.TOOL,
        x: 60,
        y: 300,
        tool_type: 'ScrapeWebsiteTool',
        name: 'Website Scraper',
        api_key_env: null
      },
      {
        id: 'agent_researcher',
        type: NODE_TYPES.AGENT,
        x: 360,
        y: 100,
        name: 'Lead_Market_Researcher',
        role: 'Senior Market Research Analyst',
        goal: 'Uncover real-time industry trends, competitor product launches, and strategic announcements',
        backstory: 'Veteran market analyst known for digging through deep search queries and surfacing high-signal intelligence.',
        llm_provider: 'OpenAI',
        model_name: 'gpt-4o',
        temperature: 0.5,
        verbose: true,
        allow_delegation: false,
        memory: true,
        max_iter: 20
      },
      {
        id: 'agent_writer',
        type: NODE_TYPES.AGENT,
        x: 360,
        y: 360,
        name: 'Executive_Brief_Writer',
        role: 'Chief Strategy Communications Editor',
        goal: 'Synthesize raw research into polished, board-ready executive summaries with actionable recommendations',
        backstory: 'Former financial journalist who crafts razor-sharp executive briefings with clear quantitative bullet points.',
        llm_provider: 'Anthropic',
        model_name: 'claude-3-5-sonnet-20241022',
        temperature: 0.7,
        verbose: true,
        allow_delegation: false,
        memory: true,
        max_iter: 15
      },
      {
        id: 'task_investigate',
        type: NODE_TYPES.TASK,
        x: 740,
        y: 100,
        name: 'Investigate_Market_Signals',
        title: 'Investigate Next-Gen AI Trends',
        description: 'Conduct exhaustive web research on the state of autonomous AI agents in 2026. Identify top 3 vendor initiatives and key industry benchmarks.',
        expected_output: 'Detailed structured report with verified source links and key quantitative milestones.',
        agent_id: 'agent_researcher',
        async_execution: false,
        output_file: 'raw_research_data.md',
        human_input: false
      },
      {
        id: 'task_synthesize',
        type: NODE_TYPES.TASK,
        x: 740,
        y: 360,
        name: 'Generate_Executive_Brief',
        title: 'Draft Board Executive Summary',
        description: 'Take findings from the market investigation task and draft an executive briefing including SWOT analysis and 3 strategic recommendations.',
        expected_output: 'A clean 5-section Markdown executive document ready for senior leadership review.',
        agent_id: 'agent_writer',
        async_execution: false,
        output_file: 'executive_market_brief_2026.md',
        human_input: false
      },
      {
        id: 'crew_config',
        type: NODE_TYPES.CREW,
        x: 1100,
        y: 220,
        name: 'MarketIntelligenceCrew',
        process: 'sequential',
        manager_llm: 'gpt-4o',
        memory: true,
        verbose: 2,
        cache: true,
        max_rpm: 120
      }
    ],
    connections: [
      { id: 'c1', type: 'tool-agent', sourceId: 'tool_serper', targetId: 'agent_researcher' },
      { id: 'c2', type: 'tool-agent', sourceId: 'tool_scrape', targetId: 'agent_researcher' },
      { id: 'c3', type: 'agent-task', sourceId: 'agent_researcher', targetId: 'task_investigate' },
      { id: 'c4', type: 'agent-task', sourceId: 'agent_writer', targetId: 'task_synthesize' },
      { id: 'c5', type: 'task-task', sourceId: 'task_investigate', targetId: 'task_synthesize' }
    ]
  },

  code_security_audit: {
    id: 'code_security_audit',
    name: 'Autonomous Code Review & Security Auditor',
    description: 'Hierarchical team inspecting repository codebases for architectural flaws, CVE vulnerabilities, and automated test coverage.',
    nodes: [
      {
        id: 'tool_dir',
        type: NODE_TYPES.TOOL,
        x: 60,
        y: 120,
        tool_type: 'DirectoryReadTool',
        name: 'Directory Reader',
        api_key_env: null
      },
      {
        id: 'tool_file',
        type: NODE_TYPES.TOOL,
        x: 60,
        y: 300,
        tool_type: 'FileReadTool',
        name: 'File Reader',
        api_key_env: null
      },
      {
        id: 'agent_architect',
        type: NODE_TYPES.AGENT,
        x: 360,
        y: 100,
        name: 'Principal_Software_Architect',
        role: 'Principal Software Architect',
        goal: 'Analyze software design patterns, modularity, edge cases, and performance bottlenecks',
        backstory: '20-year veteran systems engineer with deep expertise in distributed architecture and clean code principles.',
        llm_provider: 'Anthropic',
        model_name: 'claude-3-5-sonnet-20241022',
        temperature: 0.3,
        verbose: true,
        allow_delegation: true,
        memory: true,
        max_iter: 25
      },
      {
        id: 'agent_secops',
        type: NODE_TYPES.AGENT,
        x: 360,
        y: 360,
        name: 'AppSec_Vulnerability_Auditor',
        role: 'Senior Application Security Specialist',
        goal: 'Identify OWASP Top 10 vulnerabilities, unescaped inputs, hardcoded secrets, and dependency CVEs',
        backstory: 'Certified ethical hacker and red team analyst specialized in finding critical attack vectors before deployment.',
        llm_provider: 'OpenAI',
        model_name: 'gpt-4o',
        temperature: 0.2,
        verbose: true,
        allow_delegation: false,
        memory: true,
        max_iter: 20
      },
      {
        id: 'task_arch_review',
        type: NODE_TYPES.TASK,
        x: 740,
        y: 100,
        name: 'Architectural_Inspection',
        title: 'Review System Design & Anti-patterns',
        description: 'Scan source code files in directory, review class hierarchy, abstraction leakages, and concurrency risks.',
        expected_output: 'Detailed code audit markdown detailing architectural grade and refactoring roadmap.',
        agent_id: 'agent_architect',
        async_execution: false,
        output_file: 'architecture_audit.md',
        human_input: false
      },
      {
        id: 'task_sec_audit',
        type: NODE_TYPES.TASK,
        x: 740,
        y: 360,
        name: 'Vulnerability_Scan',
        title: 'Conduct OWASP Security Vulnerability Audit',
        description: 'Examine code logic for SQLi, XSS, insecure deserialization, privilege escalations, and exposed API tokens.',
        expected_output: 'Security triage matrix categorizing Critical, High, Medium severity findings with patch diffs.',
        agent_id: 'agent_secops',
        async_execution: false,
        output_file: 'security_vulnerability_matrix.md',
        human_input: false
      },
      {
        id: 'crew_config',
        type: NODE_TYPES.CREW,
        x: 1100,
        y: 220,
        name: 'CodeSecurityCrew',
        process: 'hierarchical',
        manager_llm: 'gpt-4o',
        memory: true,
        verbose: 2,
        cache: true,
        max_rpm: 90
      }
    ],
    connections: [
      { id: 'c1', type: 'tool-agent', sourceId: 'tool_dir', targetId: 'agent_architect' },
      { id: 'c2', type: 'tool-agent', sourceId: 'tool_file', targetId: 'agent_architect' },
      { id: 'c3', type: 'tool-agent', sourceId: 'tool_file', targetId: 'agent_secops' },
      { id: 'c4', type: 'agent-task', sourceId: 'agent_architect', targetId: 'task_arch_review' },
      { id: 'c5', type: 'agent-task', sourceId: 'agent_secops', targetId: 'task_sec_audit' },
      { id: 'c6', type: 'task-task', sourceId: 'task_arch_review', targetId: 'task_sec_audit' }
    ]
  },

  offline_ollama: {
    id: 'offline_ollama',
    name: '100% Local Offline Ollama Crew',
    description: 'Completely private, local AI pipeline using Ollama. Zero external API calls, 100% on-premise document processing.',
    nodes: [
      {
        id: 'agent_local_thinker',
        type: NODE_TYPES.AGENT,
        x: 180,
        y: 160,
        name: 'Local_Research_Specialist',
        role: 'Local Offline Intelligence Specialist',
        goal: 'Analyze on-premise documents securely without sending data to external cloud APIs',
        backstory: 'Privacy-focused intelligence analyst specialized in processing proprietary enterprise documents on-premise without network dependencies.',
        llm_provider: 'Ollama (Local Offline)',
        model_name: 'ollama/llama3.2:latest',
        temperature: 0.6,
        verbose: true,
        allow_delegation: false,
        memory: false,
        max_iter: 15
      },
      {
        id: 'task_local_summarize',
        type: NODE_TYPES.TASK,
        x: 620,
        y: 160,
        name: 'Synthesis_Task',
        title: 'Synthesis Task',
        description: 'Read the target input notes and generate a structured checklist of action items and takeaways.',
        expected_output: 'A Markdown formatted summary with actionable next steps.',
        agent_id: 'agent_local_thinker',
        async_execution: false,
        output_file: 'local_action_items.md',
        human_input: false
      },
      {
        id: 'crew_config',
        type: NODE_TYPES.CREW,
        x: 1020,
        y: 160,
        name: 'PrivateLocalCrew',
        process: 'sequential',
        manager_llm: null,
        memory: false,
        verbose: 1,
        cache: true,
        max_rpm: 60
      }
    ],
    connections: [
      { id: 'c1', type: 'agent-task', sourceId: 'agent_local_thinker', targetId: 'task_local_summarize' }
    ]
  },

  malayalam_corpus_pipeline: {
    id: 'malayalam_corpus_pipeline',
    name: 'Malayalam Corpus Builder & Trainer',
    description: 'Autonomous crawling, Unicode NFKC & Chillu standardization, LLM-as-a-judge quality critic, and Human-in-the-Loop review queue handoff.',
    nodes: [
      {
        id: 'agent_mal_crawler',
        type: NODE_TYPES.AGENT,
        x: 100,
        y: 120,
        name: 'Malayalam_Web_Crawler',
        role: 'Internet Crawler & Archive Scraper',
        goal: 'Extract high-value regional Malayalam news, Wikipedia dumps, and CommonCrawl archives',
        backstory: 'High-throughput web scraping specialist focused on discovering Malayalam regional texts from Mathrubhumi, Manorama, and cultural archives.',
        llm_provider: 'Groq (Ultra-Fast Llama)',
        model_name: 'groq/llama-3.3-70b-versatile',
        temperature: 0.3,
        verbose: true,
        allow_delegation: false,
        memory: false,
        max_iter: 10
      },
      {
        id: 'tool_mal_crawler',
        type: NODE_TYPES.TOOL,
        x: 100,
        y: 420,
        name: 'CrawlerTool',
        tool_type: 'MalayalamWebCrawlerTool',
        config: {}
      },
      {
        id: 'task_mal_crawl',
        type: NODE_TYPES.TASK,
        x: 480,
        y: 120,
        name: 'Crawl_Malayalam_Sources_Task',
        title: 'Crawl Regional Malayalam Portals',
        description: 'Scrape regional news RSS feeds, Wikipedia article dumps, and public archives, streaming raw HTML and text.',
        expected_output: 'Raw extracted Malayalam articles with source URLs and metadata in JSON format.',
        agent_id: 'agent_mal_crawler',
        async_execution: false,
        output_file: 'data/raw_crawled_articles.json',
        human_input: false
      },
      {
        id: 'agent_mal_cleaner',
        type: NODE_TYPES.AGENT,
        x: 860,
        y: 120,
        name: 'Malayalam_Morphological_Cleaner',
        role: 'Morphological Cleaner & Unicode Normalizer',
        goal: 'Enforce NFKC, standardize atomic Chillus (ൺ,ൻ,ർ,ൽ,ൾ,ൿ), filter PII, and discard < 60% Malayalam density',
        backstory: 'Linguistic computational expert specializing in Dravidian script normalization and atomic Unicode 5.1+ chillu transformations.',
        llm_provider: 'Google Gemini',
        model_name: 'gemini/gemini-2.0-flash',
        temperature: 0.2,
        verbose: true,
        allow_delegation: false,
        memory: false,
        max_iter: 15
      },
      {
        id: 'tool_mal_cleaner',
        type: NODE_TYPES.TOOL,
        x: 860,
        y: 420,
        name: 'CleanerTool',
        tool_type: 'MalayalamUnicodeCleanerTool',
        config: {}
      },
      {
        id: 'task_mal_clean',
        type: NODE_TYPES.TASK,
        x: 1240,
        y: 120,
        name: 'Unicode_Normalize_And_PII_Filter_Task',
        title: 'Normalize Unicode & Standardize Chillus',
        description: 'Convert legacy ZWJ sequences to atomic Chillus, apply NFKC, redact phone/emails, and enforce >= 60% Malayalam density.',
        expected_output: 'Normalized and sanitized Malayalam text batches with character density scores.',
        agent_id: 'agent_mal_cleaner',
        async_execution: false,
        output_file: 'data/normalized_malayalam.json',
        human_input: false
      },
      {
        id: 'agent_mal_critic',
        type: NODE_TYPES.AGENT,
        x: 1620,
        y: 120,
        name: 'Malayalam_Fluency_Critic',
        role: 'Quality & Fluency Critic (LLM-as-a-Judge)',
        goal: 'Evaluate sentence structure, validate agglutination, flag translationese, and queue batches for Human Review',
        backstory: 'Native linguistic evaluator that audits grammatical cohesion, sandhi correctness, and flags awkward machine translation artifacts.',
        llm_provider: 'Groq (Ultra-Fast Llama)',
        model_name: 'groq/llama-3.3-70b-versatile',
        temperature: 0.4,
        verbose: true,
        allow_delegation: false,
        memory: false,
        max_iter: 12
      },
      {
        id: 'tool_mal_critic',
        type: NODE_TYPES.TOOL,
        x: 1620,
        y: 420,
        name: 'CriticTool',
        tool_type: 'MalayalamFluencyCriticTool',
        config: {}
      },
      {
        id: 'task_mal_critic',
        type: NODE_TYPES.TASK,
        x: 2000,
        y: 120,
        name: 'Quality_Critic_And_HITL_Stage_Task',
        title: 'Fluency Audit & HITL Staging',
        description: 'Score sentence structure, flag translationese, and write pending batches to data/pending_approval/ for human operator review.',
        expected_output: 'Pending approval JSON batch staged for human review in the Dataset Review Queue.',
        agent_id: 'agent_mal_critic',
        async_execution: false,
        output_file: 'data/pending_approval/batch_malayalam_curated.json',
        human_input: true
      },
      {
        id: 'crew_config',
        type: NODE_TYPES.CREW,
        x: 2380,
        y: 120,
        name: 'MalayalamCorpusCrew',
        process: 'sequential',
        manager_llm: null,
        memory: false,
        verbose: 1,
        cache: true,
        max_rpm: 60
      }
    ],
    connections: [
      { id: 'c1', type: 'tool-agent', sourceId: 'tool_mal_crawler', targetId: 'agent_mal_crawler' },
      { id: 'c2', type: 'agent-task', sourceId: 'agent_mal_crawler', targetId: 'task_mal_crawl' },
      { id: 'c3', type: 'task-task', sourceId: 'task_mal_crawl', targetId: 'task_mal_clean' },
      { id: 'c4', type: 'tool-agent', sourceId: 'tool_mal_cleaner', targetId: 'agent_mal_cleaner' },
      { id: 'c5', type: 'agent-task', sourceId: 'agent_mal_cleaner', targetId: 'task_mal_clean' },
      { id: 'c6', type: 'task-task', sourceId: 'task_mal_clean', targetId: 'task_mal_critic' },
      { id: 'c7', type: 'tool-agent', sourceId: 'tool_mal_critic', targetId: 'agent_mal_critic' },
      { id: 'c8', type: 'agent-task', sourceId: 'agent_mal_critic', targetId: 'task_mal_critic' }
    ]
  }
};
