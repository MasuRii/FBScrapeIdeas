# CHANGELOG


## v0.8.3 (2025-12-21)

### ✨

- ✨ feat(ci): enable automatic releases on every master commit
  ([`d8c1504`](https://github.com/MasuRii/FBScrapeIdeas/commit/d8c1504ce57abb0c98bbfa823d614cfde06e136e))

Configure semantic-release to guarantee version bumps on all commits:

- Add `force: "patch"` to semantic-release action for guaranteed bumps - Update build/release job
  conditionals to always run on success - Add `default_bump_level = "patch"` as fallback for
  unrecognized commits - Expand emoji list from 8 to 40+ common commit emojis - Enable
  `allow_zero_version = true` for pre-1.0 development

This ensures every commit to master triggers a new release, eliminating "no bump" scenarios that
  previously blocked the pipeline.

### 🐛

- 🐛 fix(ci): use integer enum for default_bump_level in semantic-release config
  ([`a3d347a`](https://github.com/MasuRii/FBScrapeIdeas/commit/a3d347a37dc0a4f190f779158b0b6125d67f64a8))

python-semantic-release v9.15.2 requires integer enum values (0-4) for default_bump_level, not
  string values. Changed from "patch" to 1.

### 🚀

- 🚀 [infra] Implement unified release pipeline
  ([`1f3e066`](https://github.com/MasuRii/FBScrapeIdeas/commit/1f3e0664468a0c9419aad9bf5fee356896510668))

📝 Summary: Refactored the release process into a single `release-pipeline.yml` to solve the GitHub
  Actions trigger limitation.

🔧 Changes: - Merged `bump-version.yml` and `release.yml` into a single, atomic pipeline. -
  Configured the build matrix to run immediately after a successful version bump. - Removed
  redundant workflow files. - Solved the issue where `GITHUB_TOKEN` tag pushes failed to trigger the
  release workflow.


## v0.8.2 (2025-12-21)

### Other

- 0.8.2 [skip ci]
  ([`eb3af3c`](https://github.com/MasuRii/FBScrapeIdeas/commit/eb3af3ce02bc37493563ff4c54fe4b632b72da38))

### 📚

- 📚 [docs] Update Quick Start instructions for interactive setup
  ([`1800b3c`](https://github.com/MasuRii/FBScrapeIdeas/commit/1800b3ce9e97557e7deff076d93db2b640925077))

📝 Summary: Corrected misleading instructions in the README and release workflow. Clarified that
  `.env` files are not required for binary releases due to the interactive setup wizard.

🔧 Changes: - Simplified the `Quick Start` guide in `.github/workflows/release.yml`. - Reorganized
  `README.md` to highlight the Binary Release as the primary path for users. - Added explicit
  mention of the interactive setup wizard to reduce user friction.


## v0.8.1 (2025-12-21)

### Other

- 0.8.1 [skip ci]
  ([`ad6fa84`](https://github.com/MasuRii/FBScrapeIdeas/commit/ad6fa84e72aae4d3867681300233226e6d9f98ed))

### 🐛

- 🐛 [infra] Fix retired macOS runner image in release workflow
  ([`31d6f0a`](https://github.com/MasuRii/FBScrapeIdeas/commit/31d6f0a220e684bc42916176bec047b3e3a053de))

📝 Summary: Updated the retired `macos-13` runner image to `macos-latest` in the release matrix to
  fix build failures.

🔧 Changes: - Updated `macos-13` to `macos-latest` in `.github/workflows/release.yml`. - Standardized
  macOS runners in the build matrix.


## v0.8.0 (2025-12-21)

### Other

- 0.7.0 [skip ci]
  ([`97cff36`](https://github.com/MasuRii/FBScrapeIdeas/commit/97cff36f2fbdcee1671b4b9b97b694e9bdb05f7c))

- Enhance Chrome WebDriver options for improved performance and resource management
  ([`1af5acd`](https://github.com/MasuRii/FBScrapeIdeas/commit/1af5acd1e4362d045f41e33194cd9487c3320659))

- Added options to disable GPU and extensions to reduce resource usage. - Included an option to
  disable CSS rendering. - Configured preferences to block images from loading to speed up scraping.

- Feat: Add limit parameter to handle_view_command for paginated post retrieval
  ([`a3fc13a`](https://github.com/MasuRii/FBScrapeIdeas/commit/a3fc13a252a1f2b378bfc97566c6d592fe974785))

- Feat: Enhance comment ID extraction in Facebook scraper with multiple methods and fallback
  generation
  ([`bb37567`](https://github.com/MasuRii/FBScrapeIdeas/commit/bb37567516a668191be6f61602ce927f3f5f5d3b))

- Feat: Enhance filtering capabilities in handle_view_command and add distinct value retrieval
  ([`f274dd1`](https://github.com/MasuRii/FBScrapeIdeas/commit/f274dd13ca94ab06a4f1845f9e575afde96b45b4))

- Feat: Implement CLI menu and command handling for Facebook scraping application
  ([`70b51d4`](https://github.com/MasuRii/FBScrapeIdeas/commit/70b51d4e4b58c4d13d8837769d0fab64b5a1a182))

- Feat: Improve post scraping logic with error handling and logging enhancements
  ([`8f6d895`](https://github.com/MasuRii/FBScrapeIdeas/commit/8f6d8954acdf60a7832b52e3a94694e9cc6b8f4f))

- Feat: modernize project for latest dependencies and Python 3.12+ compatibility
  ([`1bb69b0`](https://github.com/MasuRii/FBScrapeIdeas/commit/1bb69b003a324a8851ce8f3eb1583fb81feff4c2))

- Pin all dependencies with version constraints in requirements.txt - Add lxml for faster
  BeautifulSoup HTML parsing - Update Selenium WebDriver setup: - Use new headless mode
  (--headless=new) for Chrome 109+ - Add anti-detection measures (navigator.webdriver hidden) -
  Update user-agent to Chrome 131 - Fix Google Gemini AI integration: - Consolidate double retry
  mechanism - Remove garbled text from error messages - Improve error handling with context - Fix
  Python 3.12+ deprecations: - Replace datetime.utcnow() with datetime.now(timezone.utc) - Add rate
  limiting with random jitter to scraper - Enable SQLite foreign key enforcement - Add input
  validation to CLI (URL, date, integer validation) - Consolidate duplicate
  get_facebook_credentials() function - Add comprehensive error handling to database stats queries

- Feat: Update CLI screenshot to reflect recent interface changes
  ([`d3f3a3f`](https://github.com/MasuRii/FBScrapeIdeas/commit/d3f3a3fdeb80a53a85e5682b6601192bdc4e2a69))

- Feat: Update CLI screenshot to reflect recent interface changes
  ([`576243e`](https://github.com/MasuRii/FBScrapeIdeas/commit/576243e9f7218f8b8c5b2b582abd000898f02778))

- Feat: Update README to enhance CLI interface details and clarify usage instructions
  ([`5420a62`](https://github.com/MasuRii/FBScrapeIdeas/commit/5420a62935fab73a9331a523fcc9063d0ae6c227))

- Fix(infra): update semantic-release branches config for v9 compatibility
  ([`5ef7e0c`](https://github.com/MasuRii/FBScrapeIdeas/commit/5ef7e0ccc32b9a400339c5ebd1e2d016f1a7234e))

- Merge pull request #4 from
  MasuRii/CLI-Menu-Organization-and-Update-&-Export-Functionality-Improvements
  ([`45a3ac9`](https://github.com/MasuRii/FBScrapeIdeas/commit/45a3ac9e9bebf86600abae8e3cae8329328823eb))

Enhance Facebook scraper with improved performance and functionality

- Merge pull request #5 from MasuRii/feature/multi-provider-ai-support
  ([`019a7b9`](https://github.com/MasuRii/FBScrapeIdeas/commit/019a7b92816b378213acc619ad5e3f2deb7eb166))

✨ Add multi-provider AI support (Gemini + OpenAI-compatible)

- Merge pull request #6 from MasuRii/feat/pr-check-workflow
  ([`2c9367f`](https://github.com/MasuRii/FBScrapeIdeas/commit/2c9367f572c02472fcdfd2c66c93fe756f85ebe3))

feat: implement GitHub PR check workflow and fix code quality issues

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

### 🔖

- 🔖 Version 0.8.0
  ([`f06e3b3`](https://github.com/MasuRii/FBScrapeIdeas/commit/f06e3b3ce5ffdd4337efe9054c68a9e1d2c6abe7))


## v0.6.0 (2025-05-30)

### Other

- Add core functionality for Facebook group scraping, AI categorization, and database management.
  Implement CLI commands for scraping, processing AI results, and viewing categorized posts. Include
  database setup and CRUD operations for managing posts.
  ([`6fc60b4`](https://github.com/MasuRii/FBScrapeIdeas/commit/6fc60b42038bd711e2e27710875aeb55dc2b0b75))

- Add Facebook login functionality and WebDriver setup for automated scraping. Update requirements
  and .gitignore to include new dependencies and files. Create auth_handler for secure credential
  management.
  ([`dacfacc`](https://github.com/MasuRii/FBScrapeIdeas/commit/dacfacc0162a419885d8ec677a602e98d1f2f373))

- Add initial project files including README, LICENSE, contributing guidelines, and example
  environment configuration. Establish project structure for Facebook group scraping and AI
  categorization.
  ([`d21344d`](https://github.com/MasuRii/FBScrapeIdeas/commit/d21344d2c7ea9be10be1bb941a4db4651f179194))

- Add initial project setup with .gitignore, config, and requirements files
  ([`d7f82dc`](https://github.com/MasuRii/FBScrapeIdeas/commit/d7f82dcf35bda36dd3915bdcbc4159233e101816))

- Create LICENSE
  ([`6a70cd3`](https://github.com/MasuRii/FBScrapeIdeas/commit/6a70cd3469a1201b7b12b34fbb0882b788e366f1))

- Delete insights.db
  ([`27c595a`](https://github.com/MasuRii/FBScrapeIdeas/commit/27c595a4e10c7d5a080579ddd9fa2d25bff16a4e))

- Enhance database schema and scraping logic to support comments and post metadata
  ([`d5be989`](https://github.com/MasuRii/FBScrapeIdeas/commit/d5be989a083969b5edaa32fdd919aad6e12a45d8))

- Updated `init_db` to create a new `Comments` table and added fields for post author details in the
  `Posts` table. - Modified `add_scraped_post` to return the internal post ID and handle existing
  posts more effectively. - Implemented `add_comments_for_post` function to insert comments related
  to scraped posts. - Updated scraping logic in `scrape_authenticated_group` to extract author
  information, post images, and comments. - Adjusted logging messages for clarity on added posts and
  comments.

- Enhance Facebook scraping functionality by adding secure credential retrieval from environment
  variables and command line prompts. Implement session validation for the Selenium WebDriver to
  ensure active login before scraping. Update logging for better error handling and debugging during
  scraping operations.
  ([`7188cca`](https://github.com/MasuRii/FBScrapeIdeas/commit/7188cca03ea2ae25c00f0c65a2ab92b4e7385180))

- Enhance logging and error handling in AI processing and scraping modules. Update database query to
  exclude posts with null content. Improve fallback mapping logic in AI categorization. Update
  insights database file.
  ([`83d0d6d`](https://github.com/MasuRii/FBScrapeIdeas/commit/83d0d6d6069c73fa478fd7fcaa41732f53943c7f))

- Enhance post viewing functionality by adding author details, post images, and comments display
  ([`d5a3132`](https://github.com/MasuRii/FBScrapeIdeas/commit/d5a31323f35b98be113b727e5c6ce6924f702c8b))

- Feat: Add .pytest_cache to .gitignore and update README with CLI screenshot
  ([`56d05c9`](https://github.com/MasuRii/FBScrapeIdeas/commit/56d05c997acdf70dc4b0193a5a06ac51b65acc87))

- Feat: Add initial CLI Menu Design document
  ([`f54acea`](https://github.com/MasuRii/FBScrapeIdeas/commit/f54aceac342f05e337bcb1cb0982a25c2ba8f23f))

This commit introduces the `docs/CLI_Menu_Design.md` file, providing an initial outline and design
  considerations for the command-line interface menu.

- Feat: Add statistics command to display summary statistics from the database
  ([`1063ab9`](https://github.com/MasuRii/FBScrapeIdeas/commit/1063ab949cc9592c3e47093b37f42317dad453a6))

- Feat: Add timestamp parsing functionality for Facebook comments and improve timestamp extraction
  in scraper
  ([`51a448f`](https://github.com/MasuRii/FBScrapeIdeas/commit/51a448fb22674f580769fdbb7eab06e19e48aaec))

- Feat: Enhance comment processing with AI analysis and update database schema for comments
  ([`d5414f4`](https://github.com/MasuRii/FBScrapeIdeas/commit/d5414f43aa0e9de4d60474825040d5b8d9a046f8))

- AI Categorization/Analysis of Individual Comments - Fixes for AI Processing and Schema Alignment

- Feat: Enhance get_all_categorized_posts function with comprehensive filtering options and update
  view command to support new filters
  ([`659db4b`](https://github.com/MasuRii/FBScrapeIdeas/commit/659db4b124a342bf32567447bafc1437521c2fa7))

- Feat: Enhance group management functionality with add, list, and remove operations
  ([`8836f6a`](https://github.com/MasuRii/FBScrapeIdeas/commit/8836f6a3e1285172f13baddef9e5da3ee8d762fa))

- Feat: Enhance timestamp parsing in scrape_authenticated_group function to handle both absolute and
  relative time formats
  ([`2873bc1`](https://github.com/MasuRii/FBScrapeIdeas/commit/2873bc1923188b80bf74eb73e9444e0a8c9fb399))

- Feat: Implement data export functionality with CSV and JSON support, including filtering options
  for posts and comments
  ([`a5b3b9e`](https://github.com/MasuRii/FBScrapeIdeas/commit/a5b3b9e745e4574e958df340aa972c6c9a22930d))

- Feat: Implement retry logic for Gemini API calls and enhance Facebook scraping functions with
  retry decorators
  ([`e028cae`](https://github.com/MasuRii/FBScrapeIdeas/commit/e028caef9791efd818c8b5975e920489fda95b6a))

- Feat: Improve handling of 'See more' button in scrape_authenticated_group function for better post
  text extraction
  ([`74d6a4e`](https://github.com/MasuRii/FBScrapeIdeas/commit/74d6a4ef00d2dc48ed5ed7c0368a2bdbe58608c0))

- Feat: Improve overlay handling and timestamp parsing in scrape_authenticated_group function
  ([`91068a4`](https://github.com/MasuRii/FBScrapeIdeas/commit/91068a42111cbb28ba5f6e390d5c6b51aee5ca3d))

- Feat: Improve post text extraction in facebook_scraper.py by enhancing "See more" button handling
  and utilizing BeautifulSoup for more robust text parsing
  ([`8ea3b25`](https://github.com/MasuRii/FBScrapeIdeas/commit/8ea3b25cae925ad704ad80ef5c2c0c8fc67610f3))

- Feat: Refactor main.py to use argparse for command handling and improve user interaction; enhance
  post text extraction in facebook_scraper.py with BeautifulSoup for better accuracy
  ([`44523ca`](https://github.com/MasuRii/FBScrapeIdeas/commit/44523ca038afd50001290404f1fb5bb87c1ea6f2))

- Feat: Refine XPath for 'See more' button in scrape_authenticated_group function to improve element
  selection
  ([`7480f06`](https://github.com/MasuRii/FBScrapeIdeas/commit/7480f06c6691ad9cf8af2e02cb6cb2f90f42ed6a))

- Feat: Remove CLI Menu Design document as it is no longer needed
  ([`9676811`](https://github.com/MasuRii/FBScrapeIdeas/commit/967681142232d9d2724b519c8490426b3a32b391))

- Feat: Update .gitignore to include memory-bank and ensure proper file handling
  ([`02c4644`](https://github.com/MasuRii/FBScrapeIdeas/commit/02c4644020e0c6e77ea8b4c9ee086861985697b4))

- Feat: Update main.py to enhance CLI functionality with clear screen, ASCII art, and improved
  command handling
  ([`55b6c14`](https://github.com/MasuRii/FBScrapeIdeas/commit/55b6c14a4703bcf0f2ca9a89f191d803a92b6c7e))

- Feat: Update menu title in main.py to reflect project name
  ([`4b1096a`](https://github.com/MasuRii/FBScrapeIdeas/commit/4b1096a467587e24671817035e7bcd4fd7c6fc0e))

- Merge pull request #1 from MasuRii/Enhance-database-schema-and-scraping-logic
  ([`1677da9`](https://github.com/MasuRii/FBScrapeIdeas/commit/1677da92f81bf4016f563d662e34fa8ca1129ea7))

Enhance database schema and scraping logic to support comments and po…

- Merge pull request #2 from MasuRii:CLI-Enhancement--Centralized-Menu-Driven-Interface
  ([`4ab3bf0`](https://github.com/MasuRii/FBScrapeIdeas/commit/4ab3bf0e23baeb1ded16680aa095475189bc00f7))

Enhance CLI functionality and improve post text extraction

- Merge pull request #3 from MasuRii/Enhanced-Error-Handling-&-Retry-Logic
  ([`ea33326`](https://github.com/MasuRii/FBScrapeIdeas/commit/ea33326d9a78566cff8f482d89193b55bf595be9))

Add enhanced comment processing and data export features

- Refactor add_scraped_post function to use 'content_text' instead of 'post_content_raw' for
  improved clarity in database insertion.
  ([`e097e30`](https://github.com/MasuRii/FBScrapeIdeas/commit/e097e306e37ebaf12f28ddbcbb0675b4c8cb89f3))

- Refactor Facebook scraping process to utilize Selenium WebDriver for authenticated sessions.
  Enhance error handling and logging throughout the scraping and database insertion workflow. Update
  database interaction methods to improve post addition logic and ensure successful connections.
  Introduce headless mode option for scraping execution.
  ([`c442a09`](https://github.com/MasuRii/FBScrapeIdeas/commit/c442a097b902d94b1268cd769ecef3d6fab59c78))

- Refactor README and add project details document
  ([`535580a`](https://github.com/MasuRii/FBScrapeIdeas/commit/535580a768c2ca8c590dd150a4d4c36abece44bc))

This commit significantly reorganizes the `README.md` for improved clarity and structure. It
  introduces a table of contents, project logo, and badges.

Key changes: - Move detailed project information (problem statement, goals, features) from
  `README.md` to a new `docs/PROJECT_DETAILS.md` file. - Update `README.md` to be a more concise
  overview with links to the new details document. - Add `.vscode` to `.gitignore` to exclude
  editor-specific files.

- Refactor: Update README for clarity and enhance .gitignore by removing unnecessary files
  ([`0f01685`](https://github.com/MasuRii/FBScrapeIdeas/commit/0f01685fb4a91984674ff94547a9876735aa37c7))

- Remove example usage comments from the main execution block in auth_handler.py
  ([`2181e99`](https://github.com/MasuRii/FBScrapeIdeas/commit/2181e99f010a4c78cff1899f521b958ccf01f3d5))

- Remove redundant XPath selector from Facebook scraper to streamline the scraping process.
  ([`01e2f92`](https://github.com/MasuRii/FBScrapeIdeas/commit/01e2f92a9ca064f41b308605fba4c8c00ae94667))

- Update .gitignore to correct formatting of .env entry and ensure proper tracking of environment
  configuration files.
  ([`0719b7a`](https://github.com/MasuRii/FBScrapeIdeas/commit/0719b7a7026983215184126d05f38402f7050c3c))

- Update .gitignore to include insights.db and ensure __pycache__ is tracked. Update binary insights
  database file.
  ([`445f635`](https://github.com/MasuRii/FBScrapeIdeas/commit/445f63583feb81755d660baea107bb0e3612baf8))

- Update CONTRIBUTING guidelines for clarity, remove LICENSE file, and enhance README with detailed
  project overview, problem statement, target audience, and value proposition. Improve setup
  instructions and project structure documentation.
  ([`6909ce1`](https://github.com/MasuRii/FBScrapeIdeas/commit/6909ce113a6e25b69982800ecb38ac10c4025426))

- Update Facebook scraper to improve timestamp extraction logic and enhance logging for better
  debugging. Add new dependencies in requirements.txt and update binary insights database.
  ([`44efff7`](https://github.com/MasuRii/FBScrapeIdeas/commit/44efff7f957dba66683dfb59aede1b93404e9f14))

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
