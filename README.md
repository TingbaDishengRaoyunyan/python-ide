# Python IDE v2

A browser-based, VS Code-like Python IDE designed for deployment behind a public domain or internal network. It supports Python execution, pip package installation, file editing, workspace management, and Docker-based isolation.

## Included

- Monaco-based editor with a VS Code-like layout
- File tree and folder navigation
- Save/open Python files in browser
- Run Python scripts from the terminal panel
- Install Python dependencies through pip
- FastAPI backend for project operations
- Docker Compose deployment
- Workspaces stored under `./workspace`
- Public deployment guidance with reverse proxy, TLS, and secure runtime options

## Default quick start

```bash
git clone https://github.com/TingbaDishengRaoyunyan/python-ide.git
cd python-ide
cp .env.example .env
docker compose up --build -d
```

Then open:

```text
http://localhost
```

## Public deployment

For real public access you should place this behind:

- Nginx or Caddy reverse proxy
- TLS via Let's Encrypt or cloud certificate
- Basic auth or OIDC if exposed to public users
- Container isolation and resource caps
- dedicated workspace mount or persistent volume

Example host mapping:

```text
https://ide.example.com
```

## Common pip packages

This environment is suitable for common Python tooling used in scraping, automation, and AI workflows. Examples:

```bash
pip install requests beautifulsoup4 pandas numpy httpx scrapy selenium playwright
pip install openai langchain transformers sentence-transformers
pip install -r requirements.txt
```

Note: large AI libraries like `torch`, `tensorflow`, or notebook stacks may require a dedicated runtime, GPU support, or a larger memory footprint. This repo keeps the default environment lightweight and production-friendly.

## Project structure

```text
.
├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── workspace/
├── .env.example
├── docker-compose.yml
├── .gitignore
├── README.md
└── LICENSE
```

## Security notes

- Do not run untrusted code directly on the host OS.
- Keep the workspace in a containerized or sandboxed environment.
- Use environment variables for secrets, not committed config.
- Restrict outbound access where needed.
- Use a proper auth layer before exposing this to the internet.

## Supported environment

- Python: 3.11
- Node/frontend: static served by nginx
- Runtime: Docker Compose
- Base OS: Ubuntu-compatible container images

## Next upgrade ideas

- multi-user auth system
- Jupyter kernel integration
- project snapshots and git sync
- AI code assistant hooks
- containerized per-project Python runtimes
- GPU runtime profile for deep learning workloads
