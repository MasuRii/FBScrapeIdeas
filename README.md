# University Group Insights Platform

[![Python Version][python-shield]][python-url]
[![License][license-shield]][license-url]
[![Issues][issues-shield]][issues-url]
[![Forks][forks-shield]][forks-url]
[![Stars][stars-shield]][stars-url]
[![Contributors][contributors-shield]][contributors-url]

A CLI-driven application to scrape and analyze Facebook group posts for insights using Selenium and Google Gemini AI.

This tool helps users identify potential capstone/thesis ideas, student problems, or other valuable insights from university Facebook group discussions by automating data collection and AI-powered categorization.

---

## 📖 Table of Contents

- [University Group Insights Platform ](#university-group-insights-platform-)
  - [📖 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [📋 Prerequisites](#-prerequisites)
  - [🚀 Getting Started](#-getting-started)
    - [Installation](#installation)
    - [Configuration](#configuration)
  - [⚙️ Usage](#️-usage)
  - [📂 Project Structure](#-project-structure)
  - [🤝 Contributing](#-contributing)
  - [📜 License](#-license)
  - [📞 Contact](#-contact)
  - [📚 Full Documentation](#-full-documentation)

---

## ✨ Features

*   **🔒 Authenticated Facebook Group Scraping:** Securely logs into Facebook to scrape posts from private or public groups.
*   **🤖 AI-Powered Post Categorization:** Leverages Google's Gemini Flash model for intelligent post analysis and categorization.
*   **💾 Local Database Storage:** Stores scraped data and AI insights in a local SQLite database.
*   **💻 Command-Line Interface (CLI):** Provides easy-to-use commands for scraping, AI processing, and data viewing.

For a detailed list of features and project goals, please see the [Full Project Details](docs/PROJECT_DETAILS.md#core-features).

---

## 🛠️ Tech Stack

*   **Language:** ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
*   **Web Scraping:**
    *   ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
    *   `webdriver-manager`
    *   `BeautifulSoup4`
*   **AI & Machine Learning:**
    *   `google-generativeai` (Google Gemini Flash)
*   **Database:**
    *   ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
*   **CLI:**
    *   `click` (or `argparse`)
*   **Utilities:**
    *   `python-dotenv`
    *   `getpass`

For more details, visit the [Technology Stack section in our documentation](docs/PROJECT_DETAILS.md#technology-stack).

---

## 📋 Prerequisites

Before you begin, ensure you have the following:
*   Python 3.9+
*   Git
*   A modern Web Browser (e.g., Chrome, Firefox)
*   Google Cloud Project & Gemini API Key

Detailed prerequisites can be found [here](docs/PROJECT_DETAILS.md#prerequisites).

---

## 🚀 Getting Started

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MasuRii/FBScrapeIdeas.git
    cd FBScrapeIdeas
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    # For Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    
    # For Windows (Command Prompt)
    python -m venv venv
    venv\Scripts\activate.bat
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Set up Environment Variables:**
    Create a `.env` file in the project root:
    ```dotenv
    # .env
    GOOGLE_API_KEY=YOUR_GEMINI_API_KEY_HERE
    FB_USER=YOUR_FACEBOOK_EMAIL_OR_USERNAME
    FB_PASS=YOUR_FACEBOOK_PASSWORD
    ```
    (Use `.env.example` as a template)

2.  **WebDriver Setup:**
    `webdriver-manager` will handle this automatically on the first run.

For detailed setup and configuration instructions, please refer to the [Setup & Installation Guide](docs/PROJECT_DETAILS.md#setup--installation) and [Configuration Details](docs/PROJECT_DETAILS.md#configuration).

---

## ⚙️ Usage

The application is run via the CLI:

```bash
python main.py <command> [options]
```

**Available Commands:**

*   `scrape`: Scrapes posts from a Facebook group.
    ```bash
    python main.py scrape --group-url "GROUP_URL" [--num-posts 50] [--headless]
    ```
*   `process-ai`: Processes scraped posts with Gemini AI.
    ```bash
    python main.py process-ai
    ```
*   `view`: Views categorized posts from the database.
    ```bash
    python main.py view [--category "Project Idea"] [--limit 10]
    ```

For comprehensive command usage and examples, see the [Usage Guide](docs/PROJECT_DETAILS.md#usage-cli-commands).

---

## 📂 Project Structure

```
FBScrapeIdeas/
├── .env                # Local environment variables (Git ignored)
├── .gitignore          # Files ignored by Git
├── README.md           # This file
├── requirements.txt    # Dependencies
├── main.py             # CLI entry point
├── ai/                 # AI related modules
├── database/           # Database setup and CRUD operations
├── scraper/            # Web scraping logic
├── docs/               # Detailed documentation
│   └── PROJECT_DETAILS.md
└── insights.db         # SQLite database (created on run)
```
A more detailed project structure can be found [here](docs/PROJECT_DETAILS.md#project-structure).

---

## 📚 Full Documentation

For a comprehensive understanding of the project, including its architecture, detailed setup, advanced usage, and ethical considerations, please refer to the [**Full Project Documentation**](docs/PROJECT_DETAILS.md).

<!-- Shields.io links -->
[python-shield]: https://img.shields.io/badge/Python-3.9%2B-blue.svg
[python-url]: https://www.python.org/downloads/
[license-shield]: https://img.shields.io/github/license/MasuRii/FBScrapeIdeas
[license-url]: https://github.com/MasuRii/FBScrapeIdeas/blob/main/LICENSE
[issues-shield]: https://img.shields.io/github/issues/MasuRii/FBScrapeIdeas
[issues-url]: https://github.com/MasuRii/FBScrapeIdeas/issues
[forks-shield]: https://img.shields.io/github/forks/MasuRii/FBScrapeIdeas
[forks-url]: https://github.com/MasuRii/FBScrapeIdeas/network/members
[stars-shield]: https://img.shields.io/github/stars/MasuRii/FBScrapeIdeas
[stars-url]: https://github.com/MasuRii/FBScrapeIdeas/stargazers
[contributors-shield]: https://img.shields.io/github/contributors/MasuRii/FBScrapeIdeas
[contributors-url]: https://github.com/MasuRii/FBScrapeIdeas/graphs/contributors
