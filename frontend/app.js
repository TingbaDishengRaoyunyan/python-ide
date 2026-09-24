(() => {
  const apiRoot = '/api';
  let editor;
  let currentPath = '';
  let fileTreeData = [];

  function setTerminal(content) {
    const el = document.getElementById('terminal-output');
    el.textContent = content;
  }

  function updatePathLabel() {
    const label = document.getElementById('path-label');
    label.textContent = currentPath || '/';
  }

  function apiRequest(path, options = {}) {
    return fetch(`${apiRoot}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    }).then(async (response) => {
      const text = await response.text();
      return text ? JSON.parse(text) : {};
    });
  }

  function renderTree(entries) {
    const container = document.getElementById('file-tree');
    container.innerHTML = '';

    const rootNode = document.createElement('div');
    rootNode.className = 'file-item';
    rootNode.textContent = 'workspace';
    rootNode.onclick = () => {
      currentPath = '';
      updatePathLabel();
      fetchFiles();
    };
    container.appendChild(rootNode);

    for (const item of entries) {
      const node = document.createElement('div');
      node.className = `file-item ${currentPath === item.path ? 'active' : ''}`;
      node.textContent = item.type === 'directory' ? `📁 ${item.name}` : `📄 ${item.name}`;
      node.onclick = () => {
        if (item.type === 'directory') {
          currentPath = item.path;
          updatePathLabel();
          fetchFiles();
        } else {
          openFile(item.path);
        }
      };
      container.appendChild(node);
    }
  }

  function fetchFiles() {
    const path = currentPath ? `?path=${encodeURIComponent(currentPath)}` : '';
    apiRequest(`/files${path}`)
      .then((data) => {
        fileTreeData = data.entries || [];
        renderTree(fileTreeData);
      })
      .catch((err) => {
        setTerminal(`Failed to load file tree: ${err}`);
      });
  }

  function ensureEditor() {
    if (editor) return;
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs' } });
    require(['vs/editor/editor.main'], () => {
      editor = monaco.editor.create(document.getElementById('editor'), {
        value: '# Python IDE\nprint("Hello world")\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
      });
    });
  }

  function openFile(path) {
    currentPath = path;
    updatePathLabel();
    apiRequest(`/file?path=${encodeURIComponent(path)}`)
      .then((data) => {
        ensureEditor();
        const model = monaco.editor.createModel(data.content || '', 'python', monaco.Uri.parse(`file:///${path}`));
        if (editor.getModel()) {
          editor.setModel(model);
        }
        setTerminal(`Opened: ${path}`);
        renderTree(fileTreeData);
      })
      .catch((err) => {
        setTerminal(`Could not open file: ${err}`);
      });
  }

  async function saveCurrentFile() {
    if (!editor || !currentPath) {
      setTerminal('No file selected.');
      return;
    }
    const content = editor.getValue();
    await apiRequest('/files/save', {
      method: 'POST',
      body: JSON.stringify({ path: currentPath, content }),
    });
    setTerminal(`Saved: ${currentPath}`);
  }

  async function runCurrentFile() {
    if (!currentPath) {
      setTerminal('Select a file first.');
      return;
    }
    const response = await apiRequest('/run', {
      method: 'POST',
      body: JSON.stringify({ path: currentPath, args: [] }),
    });
    setTerminal(`Exit code: ${response.exit_code}\nSTDOUT:\n${response.stdout || ''}\nSTDERR:\n${response.stderr || ''}`);
  }

  async function installPackages() {
    const packages = prompt('Install packages (comma separated):', 'requests beautifulsoup4 pandas');
    if (!packages) return;
    const cleaned = packages.split(',').map((item) => item.trim()).filter(Boolean);
    if (!cleaned.length) {
      setTerminal('No packages provided.');
      return;
    }

    const response = await apiRequest('/pip/install', {
      method: 'POST',
      body: JSON.stringify({ packages: cleaned }),
    });

    setTerminal(`pip install ${cleaned.join(' ')}\nExit code: ${response.exit_code}\n${response.stdout || ''}\n${response.stderr || ''}`);
  }

  async function createFile() {
    const name = prompt('File name:', 'script.py');
    if (!name) return;
    const path = currentPath ? `${currentPath}/${name}` : name;
    await apiRequest('/files/create', {
      method: 'POST',
      body: JSON.stringify({ path, kind: 'file' }),
    });
    await fetchFiles();
    openFile(path);
  }

  async function createFolder() {
    const name = prompt('Folder name:', 'new-folder');
    if (!name) return;
    const path = currentPath ? `${currentPath}/${name}` : name;
    await apiRequest('/files/create', {
      method: 'POST',
      body: JSON.stringify({ path, kind: 'directory' }),
    });
    await fetchFiles();
  }

  window.addEventListener('DOMContentLoaded', () => {
    ensureEditor();
    fetchFiles();
    updatePathLabel();

    document.getElementById('save-btn').onclick = saveCurrentFile;
    document.getElementById('run-btn').onclick = runCurrentFile;
    document.getElementById('pip-btn').onclick = installPackages;
    document.getElementById('new-file-btn').onclick = createFile;
    document.getElementById('new-folder-btn').onclick = createFolder;
    document.getElementById('refresh-btn').onclick = fetchFiles;
  });
})();
