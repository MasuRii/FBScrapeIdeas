# CHANGELOG


## v0.7.0 (2025-12-21)

### Other

- Update README.md
  ([`9a9b509`](https://github.com/MasuRii/FBScrapeIdeas/commit/9a9b509660d4812e1a37193aa1667f86673fd0c4))

- Update README.md
  ([`3d45e3e`](https://github.com/MasuRii/FBScrapeIdeas/commit/3d45e3e87199f360c68ed193238a7712577a7577))

- Update README.md
  ([`111e195`](https://github.com/MasuRii/FBScrapeIdeas/commit/111e19508f4a4970f36328bac0d3cc670f5c0042))

### ✨

- ✨ (infra) Add release workflow and robust credential management
  ([`e2829b4`](https://github.com/MasuRii/FBScrapeIdeas/commit/e2829b473c9af4555748dfdd415b287ab1f2b7bb))

📝 Summary: Implements a fully automated GitHub Actions release workflow and overhauls the credential
  management system.

🔧 Changes: - Added `.github/workflows/release.yml` for automated releases - Created `version.py` for
  centralized version tracking - Updated `config.py` with enhanced configuration loading -
  Refactored `main.py` and `cli/menu_handler.py` to utilize new config system - Updated database
  schemas in `database/db_setup.py` and queries in `database/crud.py`

- ✨ (infra) Implement GitHub PR check workflow and fix code quality issues
  ([`539e2b5`](https://github.com/MasuRii/FBScrapeIdeas/commit/539e2b54f432d07c88c0d21c8e9be1f62d6b68f9))

📝 Summary: This commit introduces a comprehensive CI/CD pipeline for Pull Requests using GitHub
  Actions, ensuring code quality through Ruff linting and automated testing.

🔧 Changes: - 🔄 Added `.github/workflows/pr-check.yml` for automated linting and testing - 🛠
  Configured Ruff in `pyproject.toml` for standardized linting and formatting - 📦 Added
  `requirements-dev.txt` for development dependencies - ♻️ Refactored 13 source files to comply with
  Ruff linting rules - 🚦 Fixed pre-existing test failures and timeouts in
  `tests/test_facebook_scraper.py` - 🧪 Improved test robustness with increased timeouts and better
  cleanup

🔗 Related: Closes #6

- ✨ [infra] Implement automated semantic versioning and release workflows
  ([`0f97e4a`](https://github.com/MasuRii/FBScrapeIdeas/commit/0f97e4a57cb60fd0c897ab18e31bcd5f4e9b9f7f))

📝 Summary: Implemented a robust, emoji-based automated versioning and release pipeline aligned with
  the project's Git agent conventions.

🔧 Changes: - Fixed branch mismatch in GitHub Actions (changed `main` to `master`). - Implemented
  `python-semantic-release` for automated versioning. - Created `bump-version.yml` workflow for
  automated tagging and changelog generation. - Updated `release.yml` to trigger exclusively on
  version tags. - Configured `pyproject.toml` to support hybrid and emoji-only commit styles. -
  Updated documentation (README and CONTRIBUTING) to match new standards.

- ✨ Add multi-provider AI support with Gemini and OpenAI compatibility
  ([`104701a`](https://github.com/MasuRii/FBScrapeIdeas/commit/104701a5a9650ce1a2f6d653bc06594849ef28ed))

📝 Summary: Implement a flexible AI provider system that supports multiple backends including Google
  Gemini and any OpenAI-compatible API (OpenAI, Ollama, LM Studio, OpenRouter, etc.).

🔧 Changes: - Add abstract AIProvider base class for consistent provider interface - Implement
  GeminiProvider with model selection support - Implement OpenAIProvider for OpenAI-compatible APIs
  (Ollama, LM Studio, OpenRouter) - Create provider factory for seamless switching between backends
  - Add custom prompts system via JSON configuration file - Extend CLI with AI Settings menu for
  provider/model configuration - Update config.py with new AI provider environment variables -
  Refactor gemini_service.py to use the new provider abstraction - Comprehensive documentation
  updates in README.md

✨ New files: - ai/base_provider.py - Abstract provider interface - ai/gemini_provider.py - Google
  Gemini implementation - ai/openai_provider.py - OpenAI-compatible implementation - ai/prompts.py -
  Centralized prompt management - ai/provider_factory.py - Factory pattern for provider creation -
  custom_prompts.example.json - Template for custom AI prompts

🔗 Related: Enables local LLM usage and provider flexibility


## v0.6.0 (2025-05-30)

### Other

- Create LICENSE
  ([`6a70cd3`](https://github.com/MasuRii/FBScrapeIdeas/commit/6a70cd3469a1201b7b12b34fbb0882b788e366f1))

- Feat: Enhance group management functionality with add, list, and remove operations
  ([`8836f6a`](https://github.com/MasuRii/FBScrapeIdeas/commit/8836f6a3e1285172f13baddef9e5da3ee8d762fa))

- Update README.md
  ([`af90853`](https://github.com/MasuRii/FBScrapeIdeas/commit/af9085302e9d48e689b19e08c2cc58edfbc88202))

- Update README.md
  ([`722648b`](https://github.com/MasuRii/FBScrapeIdeas/commit/722648b571f963a3fd78b55a78381487bed16bbc))

- Update README.md
  ([`f39e13b`](https://github.com/MasuRii/FBScrapeIdeas/commit/f39e13b85eb099950ddd43e6c0e80e4c37811298))

- Update README.md
  ([`68f3313`](https://github.com/MasuRii/FBScrapeIdeas/commit/68f33132dfb65f9f67dc569611b1291d783a5147))

- Update README.md
  ([`c068a80`](https://github.com/MasuRii/FBScrapeIdeas/commit/c068a809be87940da062a7e5d4d2d8a1b224bf70))
