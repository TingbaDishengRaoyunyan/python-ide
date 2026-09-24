(() => {
  const apiRoot = '/api';
  let editor;
  let currentPath = '';

  const $ = (id) => document.getElementById(id);
  const token = () => localStorage.getItem('python-ide-token');

  const setOutput = (text) => {
    $('terminal-output').textContent = text;
  };

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${apiRoot}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
        ...(options.headers || {}),
      },
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    return data;
  }

  function showAuth() {
    $('auth-screen').classList.remove('hidden');
    $('app-shell').classList.add('hidden');
  }

  function showApp(user) {
    $('auth-screen').classList.add('hidden');
    $('app-shell').classList.remove('hidden');
    $('user-label').textContent = `${user.username} (${user.role})`;
    const isAdmin = ['owner', 'admin'].includes(user.role);
    $('admin-tab').classList.toggle('hidden', !isAdmin);
    loadFiles();
  }

  async function authenticate(endpoint) {
    try {
      const payload = {
        username: $('username').value.trim(),
        password: $('password').value,
      };
      const result = await apiRequest(endpoint, { method: 'POST', body: JSON.stringify(payload) });
      localStorage.setItem('python-ide-token', result.token);
      showApp(result.user);
    } catch (err) {
      $('auth-output').textContent = err.message;
    }
  }

  function ensureEditor() {
    if (editor) return;
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs' } });
    require(['vs/editor/editor.main'], () => {
      editor = monaco.editor.create($('editor'), {
        value: '# Python IDE\nprint("Hello world")\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
      });
    });
  }

  async function loadFiles() {
    try {
      const response = await apiRequest(`/files${currentPath ? `?path=${encodeURIComponent(currentPath)}` : ''}`);
      const entries = response.entries || [];
      const tree = $('file-tree');
      tree.innerHTML = '';
      const root = document.createElement('div');
      root.className = 'file-item';
      root.textContent = 'workspace';
      root.onclick = () => {
        currentPath = '';
        $('path-label').textContent = '/';
        loadFiles();
      };
      tree.appendChild(root);

      entries.forEach((entry) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.textContent = `${entry.type === 'directory' ? '📁' : '📄'} ${entry.name}`;
        item.onclick = () => {
          if (entry.type === 'directory') {
            currentPath = entry.path;
            $('path-label').textContent = currentPath;
            loadFiles();
          } else {
            openFile(entry.path);
          }
        };
        tree.appendChild(item);
      });
      $('path-label').textContent = currentPath || '/';
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function openFile(path) {
    currentPath = path;
    try {
      const data = await apiRequest(`/file?path=${encodeURIComponent(path)}`);
      ensureEditor();
      editor.setValue(data.content || '');
      $('path-label').textContent = path;
      setOutput(`Opened: ${path}`);
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function saveCurrentFile() {
    if (!editor || !currentPath) {
      setOutput('Select a file first.');
      return;
    }
    try {
      await apiRequest('/files/save', {
        method: 'POST',
        body: JSON.stringify({ path: currentPath, content: editor.getValue() }),
      });
      setOutput(`Saved: ${currentPath}`);
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function createItem(kind) {
    const defaultName = kind === 'file' ? 'script.py' : 'new-folder';
    const name = prompt(kind === 'file' ? 'File name:' : 'Folder name:', defaultName);
    if (!name) return;
    const targetPath = currentPath ? `${currentPath}/${name}` : name;
    try {
      await apiRequest('/files/create', {
        method: 'POST',
        body: JSON.stringify({ path: targetPath, kind }),
      });
      currentPath = '';
      loadFiles();
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function runCurrentFile() {
    if (!currentPath) {
      setOutput('Select a file first.');
      return;
    }
    try {
      const result = await apiRequest('/run', {
        method: 'POST',
        body: JSON.stringify({ path: currentPath, args: [] }),
      });
      setOutput(`Exit code: ${result.exit_code}\nSTDOUT:\n${result.stdout || ''}\nSTDERR:\n${result.stderr || ''}`);
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function pipInstall() {
    const input = prompt('Packages (comma separated):', 'requests pandas');
    if (!input) return;
    const packages = input.split(',').map((x) => x.trim()).filter(Boolean);
    if (!packages.length) return;
    try {
      const result = await apiRequest('/pip/install', {
        method: 'POST',
        body: JSON.stringify({ packages }),
      });
      setOutput(`Exit code: ${result.exit_code}\nSTDOUT:\n${result.stdout || ''}\nSTDERR:\n${result.stderr || ''}`);
    } catch (err) {
      setOutput(err.message);
    }
  }

  async function reloadUsers() {
    const query = $('user-search').value.trim();
    try {
      const result = await apiRequest(`/admin/users?q=${encodeURIComponent(query)}`);
      const rows = result.users || [];
      const body = $('users-body');
      body.innerHTML = '';

      rows.forEach((user) => {
        const row = document.createElement('tr');
        const perms = Object.entries(user.permissions || {})
          .map(([key, enabled]) => `
            <label>
              <input type="checkbox" data-permission="${key}" ${enabled ? 'checked' : ''} />
              ${key}
            </label>
          `)
          .join('');

        row.innerHTML = `
          <td>${user.username}</td>
          <td>
            <select class="role-select">
              <option value="user" ${user.role === 'user' ? 'selected' : ''}>user</option>
              <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>admin</option>
            </select>
          </td>
          <td>${perms}</td>
          <td>
            <button class="save-user-btn">Save</button>
            <button class="delete-user-btn">Delete</button>
          </td>
        `;

        const saveBtn = row.querySelector('.save-user-btn');
        const deleteBtn = row.querySelector('.delete-user-btn');
        const select = row.querySelector('.role-select');

        saveBtn.onclick = async () => {
          await apiRequest(`/admin/users/${encodeURIComponent(user.username)}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role: select.value }),
          });
          row.querySelectorAll('input[data-permission]').forEach((input) => {
            apiRequest(`/admin/users/${encodeURIComponent(user.username)}/permission`, {
              method: 'PATCH',
              body: JSON.stringify({ permission: input.dataset.permission, enabled: input.checked }),
            }).catch((err) => setOutput(err.message));
          });
          reloadUsers();
        };

        deleteBtn.onclick = async () => {
          if (!confirm(`Delete ${user.username}?`)) return;
          await apiRequest(`/admin/users/${encodeURIComponent(user.username)}`, { method: 'DELETE' });
          reloadUsers();
        };

        body.appendChild(row);
      });

      const overview = $('overview');
      const info = await apiRequest('/admin/overview');
      overview.innerHTML = `
        <div class="card">Users: ${info.users}</div>
        <div class="card">Admins: ${info.admins}</div>
        <div class="card">Workspaces: ${info.workspaces}</div>
      `;
    } catch (err) {
      setOutput(err.message);
    }
  }

  window.addEventListener('DOMContentLoaded', async () => {
    ensureEditor();

    $('login-btn').onclick = () => authenticate('/auth/login');
    $('register-btn').onclick = () => authenticate('/auth/register');
    $('logout-btn').onclick = () => {
      localStorage.removeItem('python-ide-token');
      showAuth();
    };

    $('save-btn').onclick = saveCurrentFile;
    $('run-btn').onclick = runCurrentFile;
    $('pip-btn').onclick = pipInstall;
    $('new-file-btn').onclick = () => createItem('file');
    $('new-folder-btn').onclick = () => createItem('directory');
    $('refresh-btn').onclick = loadFiles;
    $('reload-users').onclick = reloadUsers;
    $('user-search').addEventListener('input', reloadUsers);

    $('ide-tab').onclick = () => {
      $('admin-panel').classList.add('hidden');
      $('ide-panel').classList.remove('hidden');
      $('ide-tab').classList.add('active');
      $('admin-tab').classList.remove('active');
    };

    $('admin-tab').onclick = () => {
      $('admin-panel').classList.remove('hidden');
      $('ide-panel').classList.add('hidden');
      $('admin-tab').classList.add('active');
      $('ide-tab').classList.remove('active');
      reloadUsers();
    };

    try {
      if (token()) {
        const result = await apiRequest('/auth/me');
        showApp(result.user);
      } else {
        showAuth();
      }
    } catch (err) {
      localStorage.removeItem('python-ide-token');
      showAuth();
    }
  });
})();
