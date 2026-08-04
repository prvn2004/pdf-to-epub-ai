# Contributing to Folio

Thank you for your interest in contributing to **Folio**! We welcome bug reports, feature proposals, documentation improvements, and pull requests.

## Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/pdf-to-epub.git
   cd pdf-to-epub
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Linux/macOS
   .\.venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and set your `OPENCODE_API_KEY`.

4. **Run the Development Server**:
   ```bash
   python server.py
   ```

## Repository Guidelines

- **Backend Architecture**: All backend domain logic resides in `app/`. Keep route handlers thin and isolate third-party library calls behind adapters in `app/clients/`.
- **Frontend Architecture**: The frontend uses native browser ES modules in `static/js/` without build steps. State mutations should be dispatched through `AppState` in `static/js/state.js`.
- **Code Style**: Follow PEP 8 guidelines for Python code and modern ES6+ standards for JavaScript.

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-new-feature`.
2. Commit your changes with clear, descriptive commit messages.
3. Test your changes locally to ensure the server starts and processes PDFs correctly.
4. Push to your fork and submit a Pull Request against `main`.

## License

By contributing to Folio, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
