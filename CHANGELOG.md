# Changelog

All notable changes to **Folio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-05

### Added
- Modular Python backend architecture (`app/` package containing `config`, `models`, `clients`, `services`, and `api` routers).
- Abstract Vision LLM client (`BaseVisionLLMClient`) and PDF Renderer interface (`BasePDFRenderer`).
- Thread-safe `SessionService` and async event queue manager.
- Modular frontend architecture separating HTML template (`templates/index.html`), design system tokens (`static/css/`), and ES modules (`static/js/`).
- Reactive `AppState` store and decoupled `SSEManager` for real-time streaming updates.
- Path traversal validation in asset route handlers.
- GitHub Open Source repository assets: `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.env.example`, and `.github/` templates.

### Changed
- Refactored single-file `server.py` into clean FastAPI application structure with `server.py` entrypoint runner.
- Replaced inline CSS/JS in `index.html` with native ES6 modules and scoped stylesheets.

---

## [0.1.0] - 2026-08-01

### Added
- Initial MVP prototype featuring PDF-to-Markdown processing using Qwen3.7 Plus.
- Real-time Server-Sent Events (SSE) streaming preview.
- Image coordinate detection and local Pillow image cropping.
- Split-view browser interface.
