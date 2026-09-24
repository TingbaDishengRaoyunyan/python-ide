# Python IDE

A browser-based VS Code-like Python IDE with pip support, Python execution, and Dockerized deployment.

## Features

- Monaco-based editor with a VS Code-like layout
- File tree and project workspace management
- Run Python scripts from the browser
- Install packages via pip from the interface
- FastAPI backend for project operations
- Docker Compose deployment for easy hosting
- Python environment isolation via `.venv`

## Stack

- Frontend: HTML/CSS/JavaScript + Monaco Editor
- Backend: FastAPI + Uvicorn
- Runtime: Python 3.11
- Deployment: Docker + Docker Compose + Nginx

## Quick start

```bash
docker compose up --build
```

Then open:

```text
http://localhost
```

## Default workspace

Files are stored under the `./workspace` directory and can be edited through the browser.

## Environment

Copy `.env.example` to `.env` if you need custom settings.

## Notes

This project is designed for easy deployment and package installation support for common Python libraries used in scraping, automation, and AI workflows.
