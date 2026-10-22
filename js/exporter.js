/**
 * Visual CrewAI Agent & Workflow Builder
 * Exporter: ZIP Generation, File Downloads & JSON State Persistence
 */

import { generateCrewProject } from './generator.js';

export class Exporter {
  constructor(onNotify) {
    this.onNotify = onNotify;
  }

  downloadString(filename, content, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }

  saveWorkflowJson(graph) {
    const jsonStr = JSON.stringify(graph, null, 2);
    const crewName = graph.nodes.find(n => n.type === 'crew')?.name || 'crewai_workflow';
    this.downloadString(`${crewName.toLowerCase()}_workflow.json`, jsonStr, 'application/json');
    if (this.onNotify) this.onNotify('Workflow JSON saved successfully!', 'success');
  }

  loadWorkflowJson(file, callback) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const graph = JSON.parse(e.target.result);
        if (callback) callback(graph);
        if (this.onNotify) this.onNotify('Workflow loaded from file!', 'success');
      } catch (err) {
        if (this.onNotify) this.onNotify(`Failed to parse workflow JSON: ${err.message}`, 'error');
      }
    };
    reader.readAsText(file);
  }

  async exportFullZip(graph) {
    if (typeof JSZip === 'undefined') {
      if (this.onNotify) this.onNotify('JSZip library not loaded. Downloading standalone python file instead.', 'warning');
      const gen = generateCrewProject(graph);
      this.downloadString('crew_runner.py', gen.singleRunnerPy);
      return;
    }

    if (this.onNotify) this.onNotify('Packaging complete CrewAI project ZIP...', 'info');

    const gen = generateCrewProject(graph);
    const zip = new JSZip();

    const crewName = gen.metadata.crewName || 'MyCrew';
    const folder = zip.folder(crewName.toLowerCase());

    // Config folder with YAMLs
    const configFolder = folder.folder('config');
    configFolder.file('agents.yaml', gen.agentsYaml);
    configFolder.file('tasks.yaml', gen.tasksYaml);

    // Python source files
    folder.file('crew.py', gen.crewPy);
    folder.file('main.py', gen.mainPy);
    folder.file('crew_runner.py', gen.singleRunnerPy);
    folder.file('.env', gen.envFile);
    folder.file('requirements.txt', gen.requirementsTxt);
    folder.file('workflow.crewai.json', JSON.stringify(graph, null, 2));

    // Custom README.md
    const readmeContent = `# ${crewName} - CrewAI Project

Generated automatically by **Visual CrewAI Agent & Workflow Builder**.

## Quick Start Guide

### 1. Create and Activate Virtual Environment
\`\`\`bash
# On Windows:
python -m venv .venv
.venv\\Scripts\\activate

# On macOS/Linux:
python3 -m venv .venv
source .venv/bin/activate
\`\`\`

### 2. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Configure API Keys
Edit the \`.env\` file in this directory and supply your secret keys:
\`\`\`bash
${gen.metadata.neededKeys.map(k => `${k}=your_key_here`).join('\n')}
\`\`\`

### 4. Execute the Crew
You have two ways to run:

**Option A (Single-File Runner):**
\`\`\`bash
python crew_runner.py
\`\`\`

**Option B (Native CrewAI Structure):**
\`\`\`bash
python main.py
# or
crewai run
\`\`\`
`;
    folder.file('README.md', readmeContent);

    // Generate ZIP file and trigger download
    try {
      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${crewName.toLowerCase()}_project.zip`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 100);
      if (this.onNotify) this.onNotify('Project ZIP successfully generated and downloaded!', 'success');
    } catch (err) {
      if (this.onNotify) this.onNotify(`Error generating ZIP: ${err.message}`, 'error');
    }
  }
}
