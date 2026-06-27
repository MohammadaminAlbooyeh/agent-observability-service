# doflow — To-Do List Application

A full-stack to-do list app built with a **React + Vite** frontend and a **FastAPI** backend, containerized with Docker Compose.

## Features
- Create, edit, delete, and toggle to-do items
- Archive/restore tasks
- Priority levels (Low / Medium / High)
- Category filtering (Personal, Work, Shopping, Health, Finance)
- Due dates with overdue indicators
- Search by title
- Stats dashboard (pending, completed, per-category counts)
- Animated progress bar
- Dark theme UI
- Docker deployment with nginx reverse proxy

## Project Structure

```
to_do_list/
├── backend/
│   ├── app.py           # FastAPI server
│   ├── Dockerfile       # Backend Docker image
│   ├── requirements.txt # Backend Python dependencies
│   └── data/
│       └── todo.db      # SQLite database
├── frontend/
│   ├── App.jsx          # Main React component
│   ├── Dockerfile       # Frontend multi-stage Docker image
│   ├── package.json     # Frontend dependencies
│   ├── vite.config.js   # Vite configuration
│   ├── nginx.conf       # Nginx config for production
│   └── src/
│       ├── components/  # React components
│       └── useTodos.js  # Custom hook for API calls
├── docker-compose.yml   # Multi-container orchestration
└── README.md            # Project documentation
```

## Prerequisites
- Docker & Docker Compose installed

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd to_do_list
   ```

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

3. **Access the app:**
   - Frontend: [http://localhost:8080](http://localhost:8080)
   - Backend API: [http://localhost:5050](http://localhost:5050)

## Development

### Backend (FastAPI)
```
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 5050
```

### Frontend (Vite + React)
```
cd frontend
npm install
npm run dev
```
Frontend runs on [http://localhost:5173](http://localhost:5173), proxies `/api` to the backend.

## API Endpoints
- `GET /todos` — List active to-dos (`?archived=true` for archived)
- `GET /stats` — Stats (total, completed, pending, per-category)
- `POST /todos` — Create a new to-do
- `PUT /todos/<id>` — Update a to-do
- `DELETE /todos/<id>` — Delete a to-do

## License
MIT
