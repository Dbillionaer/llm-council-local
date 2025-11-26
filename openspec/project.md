# Project Context

## Purpose
LLM Council is a 3-stage deliberation system where multiple LLMs collaborate to answer user questions. Instead of asking a single LLM, queries are sent to a "council" of different models that review and rank each other's work, culminating in a synthesized final response from a designated Chairman LLM. The key innovation is anonymized peer review to prevent models from playing favorites.

## Tech Stack

### Backend (Python 3.10+)
- **FastAPI** - Async web framework for API endpoints
- **httpx** - Async HTTP client for OpenRouter API calls
- **Pydantic** - Data validation and serialization
- **uvicorn** - ASGI server for FastAPI
- **python-dotenv** - Environment variable management

### Frontend (React + Vite)
- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **react-markdown** - Markdown rendering for LLM responses
- **ESLint** - Code linting

### Infrastructure
- **LM Studio API** - Local AI inference server for hosting multiple models
- **JSON files** - Local storage for conversations (`data/conversations/`)
- **uv** - Python package management
- **npm** - JavaScript package management

## Project Conventions

### Code Style
- Backend uses relative imports (`from .module import ...`)
- React components use JSX with functional style and hooks
- Backend runs on port 8001 (not 8000 to avoid conflicts)
- Frontend runs on port 5173 (Vite default)
- All markdown content wrapped in `.markdown-content` class for consistent spacing

### Architecture Patterns
- **3-Stage Council Process**:
  1. Stage 1: Parallel collection of individual model responses
  2. Stage 2: Anonymized peer review and ranking (models evaluate "Response A, B, C" without knowing origins)
  3. Stage 3: Chairman synthesis of final answer using all context
- **Graceful degradation**: Continue with successful responses if some models fail
- **Async/parallel execution**: Minimize latency through concurrent API calls
- **Client-side de-anonymization**: Models see anonymous labels, UI shows real model names

### Testing Strategy
- Manual testing with `test_openrouter.py` for API connectivity
- No formal test suite (project is experimental/vibe-coded)
- Validate ranking parsing through UI inspection
- Test different model configurations before deployment

### Git Workflow
- Simple branching - primarily main branch development
- Code is ephemeral by design (meant to be modified by users with LLM assistance)
- No formal CI/CD pipeline

## Domain Context

### LLM Council Workflow
1. User submits query via React frontend
2. Backend creates conversation ID and stores user message
3. Parallel Stage 1: Query all council models simultaneously
4. Stage 2: Anonymize responses and have each model rank others' work
5. Calculate aggregate rankings from peer evaluations
6. Stage 3: Chairman model synthesizes final answer with full context
7. Return structured response with all stages and metadata

### Model Configuration
- Council models defined in `models.json` configuration file
- Default council: Phi-4 Mini Reasoning, Apollo 4B Thinking, AI21 Jamba Reasoning
- Chairman model: Qwen3-4B Thinking
- Runtime configuration changes without code modifications
- Fallback to hardcoded defaults if configuration file missing
- All models run locally via LM Studio server

### UI Transparency
- All raw model outputs inspectable via tabbed interface
- Parsed rankings displayed below raw text for validation
- De-anonymization explained to users for transparency
- Aggregate rankings show average position and vote distribution

## Important Constraints

### Technical
- LM Studio server availability and local network connectivity
- Must run backend as `python -m backend.main` from project root
- CORS configured only for localhost development
- No authentication or user management
- JSON file storage limits scalability
- Models must be pre-loaded in LM Studio before use

### Business
- Experimental project - no formal support or maintenance
- Designed for personal/educational use with local AI
- No API costs (runs entirely locally)
- Requires sufficient local compute resources

### Regulatory
- Complete data privacy (all processing happens locally)
- No data sent to external services
- User responsible for appropriate use of LLM outputs
- Inherits licensing requirements of local models used

## External Dependencies

### Required Services
- **LM Studio** (`http://192.168.1.111:11434/v1/chat/completions`)
  - Local AI inference server
  - OpenAI-compatible API format
  - No authentication required (local network)
  - Hosts: Phi-4, Qwen3-4B, Gemma-3N, Olmo-3-7B models

### Key Dependencies
- **React ecosystem** for frontend rendering and state management
- **FastAPI ecosystem** for async backend operations
- **uv package manager** for Python dependency resolution
- **Vite bundler** for frontend development and building
- **LM Studio** for local model hosting and inference

### Runtime Requirements
- Node.js for frontend development
- Python 3.10+ for backend
- Local network access to LM Studio server
- Modern browser with ES modules support
- Sufficient GPU/CPU resources for local AI inference
