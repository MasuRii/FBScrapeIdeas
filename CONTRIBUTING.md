# Contributing to University Group Insights Platform

Thank you for your interest in contributing to this project! We welcome contributions from the community. Please follow these guidelines to help us maintain a smooth and effective development process.

## How to Report Bugs

If you find a bug, please report it by opening a new issue on the GitHub repository. When reporting a bug, please include:

*   A clear and concise description of the bug.
*   Steps to reproduce the behavior.
*   Expected behavior.
*   Screenshots or error messages (if applicable).
*   Your operating system and Python version.

## How to Suggest Enhancements

We welcome suggestions for new features or improvements. Please open a new issue on GitHub to propose an enhancement. Describe the enhancement and explain why you think it would be valuable.

## Pull Request Process

1.  **Fork the repository** and clone it to your local machine.
2.  **Create a new branch** from `master` for your contribution.
3.  **Implement your changes.** Make sure to follow any existing coding conventions.
4.  **Test your changes** thoroughly.
5.  **Commit your changes** with clear and descriptive commit messages (see **Conventional Commits** below).
6.  **Push your branch** to your fork.
7.  **Open a Pull Request** targeting the `master` branch of the original repository.
8.  Provide a clear title and description for your pull request, explaining the changes you've made.

## Emoji-Enhanced Conventional Commits

We use a strict **Emoji-Enhanced Conventional Commits** format to ensure automated versioning and changelog generation works correctly. Our `git` agent is trained to handle this automatically, but manual contributors must adhere to these rules.

### 1. Title Structure

The first line of the commit message (the title) must follow this format:

```text
<emoji> [optional scope] <description>
```

-   **Emoji**: Select one from the table below.
-   **Scope**: Optional, wrapped in brackets (e.g., `[cli]`, `[auth]`).
-   **Description**: Brief summary in imperative mood (e.g., "add feature" not "added feature"). Max 50 chars.

### 2. Emoji Reference & Versioning

The emoji determines the semantic version bump (Major, Minor, or Patch).

| Emoji | Meaning | Version Impact |
| :---: | :--- | :--- |
| 🚨 | Breaking Change | **MAJOR** |
| ✨ | New Feature | **MINOR** |
| 🐛 | Bug Fix | **PATCH** |
| 🔒 | Security Fix | **PATCH** |
| 🛠 | Refactoring | **PATCH** |
| ⚡️ | Performance | **PATCH** |
| 📚 | Documentation | **PATCH** |
| 🏗 | Infrastructure | **PATCH** |
| ♻️ | Code Cleanup | **PATCH** |
| 🚦 | Tests | **PATCH** |
| 🎨 | Styling/UI | **PATCH** |
| 📦 | Dependencies | **PATCH** |
| 🔖 | Release/Tags | **PATCH** |

### 3. Mandatory Body Structure

The body of the commit message **must** follow this structure:

```text
📝 Summary: [One sentence explaining the 'why']
🔧 Changes:
- [Bulleted list of specific changes]
- [Keep it technical and concise]
⚠️ Breaking: [Optional: Description of breaking changes]
🔗 Related: [Optional: Issue numbers or links]
```

### Note on Automation

If you are using our `git` agent, it will automatically format your commits this way. If you are committing manually, strict adherence is required for the CI/CD pipeline to function correctly.

### Automated Versioning

**Important:** We use an automated release pipeline.
*   **Do not manually edit `version.py` or `pyproject.toml`**.
*   The system will automatically calculate the next version number based on your commit messages when changes are merged to `master`.

## Coding Conventions

For now, follow standard Python practices and aim for readable code.

## Contact

If you have any questions about contributing, please open an issue or reach out to the repository maintainers.
