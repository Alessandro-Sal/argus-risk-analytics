# Contributing to ARGUS — Risk Analytics Platform

Thank you for your interest in contributing to **ARGUS**! We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## 🚀 Getting Started

### 1. Fork & Clone
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/argus-risk-analytics.git
   cd argus-risk-analytics
   ```

### 2. Environment Setup
Create a virtual environment and install the development dependencies:
```bash
python -m venv venv

# On Windows:
.\venv\Scripts\activate

# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

---

## 🧪 Running Tests & Quality Checks

Before submitting a Pull Request, ensure that all unit tests pass:

```bash
pytest
```

We also enforce code formatting and linting via `ruff`:
```bash
ruff check .
```

---

## 🌿 Branching Strategy & Pull Requests

1. Create a feature branch off `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit your changes with clear, descriptive commit messages following Conventional Commits (`feat: ...`, `fix: ...`, `docs: ...`).
3. Push to your branch and open a Pull Request against `main`.
4. Ensure CI tests pass on your Pull Request.

---

## 💬 Reporting Issues

If you find a bug or have a feature request:
- Search existing [Issues](https://github.com/Alessandro-Sal/argus-risk-analytics/issues) to avoid duplicates.
- Open a new Issue with a clear title, reproduction steps, expected behavior, and environment details.

Thank you for helping make ARGUS better!
