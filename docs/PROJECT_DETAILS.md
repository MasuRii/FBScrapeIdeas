# University Group Insights Platform

A CLI-driven application designed to scrape posts from a specified university Facebook group using Selenium and user-provided credentials. It then leverages Google's Gemini 2.0 Flash for AI-powered categorization of these posts, storing the structured insights in a local SQLite database. This tool aims to help users identify potential capstone/thesis ideas, student problems, or other valuable insights from group discussions.

## Overview

This tool automates the process of gathering and analyzing posts from university-specific Facebook groups. By handling authenticated access and utilizing advanced AI for categorization, it provides an efficient way to extract meaningful information from online student communities.

### Problem Statement

Manually sifting through numerous Facebook group posts, especially those requiring login, to find relevant ideas, problems, or trends is time-consuming and inefficient. Potential valuable insights for academic projects or understanding student needs can be easily missed.

### Target Audience

Primarily students looking for capstone/thesis ideas, researchers, or university faculty/staff interested in understanding student concerns and interests within their academic community.

### Value Proposition

Automates the discovery and categorization of student-generated ideas and problems from a university Facebook group, including those requiring authenticated access. It saves time and surfaces valuable insights for academic and research purposes by leveraging advanced AI (Gemini 2.0 Flash) for efficient, structured processing.

### Goals & Objectives

*   Successfully scrape relevant posts (content, URL, timestamp) from the target Facebook group using Selenium and user-provided credentials.
*   Accurately categorize posts using Google's Gemini 2.0 Flash based on predefined themes (e.g., "problem statement," "project idea"), utilizing structured JSON output.
*   Efficiently process posts by batching them for the Gemini API.
*   Store scraped and categorized posts in a structured SQLite database for easy querying and review via the CLI.
*   Provide clear CLI commands to trigger scraping, AI processing, and viewing of posts.

## Core Features

*   **Authenticated Facebook Group Scraping:** Utilizes Selenium to automate browser interaction, enabling login to Facebook with user-provided credentials to access and scrape posts (content, URL, timestamp) from specified private or public groups.
*   **AI-Powered Post Categorization:** Integrates with Google's Gemini 2.0 Flash model. Scraped post text is analyzed and categorized into predefined themes (e.g., "Problem Statement," "Project Idea"). This process uses batching for API efficiency and expects structured JSON output from the AI.
*   **Local Database Storage:** Scraped posts and their corresponding AI-generated categorizations are stored persistently in a local SQLite database (`insights.db`), allowing for offline access and analysis.
*   **Command-Line Interface (CLI):** Offers a user-friendly CLI for interacting with the application, including commands to initiate scraping, trigger AI processing of new posts, and view stored/categorized data with filtering options.

## Technology Stack

*   **Programming Language:** Python (3.9+)
*   **Web Scraping / Browser Automation:**
    *   `Selenium`: For browser automation and interaction with Facebook.
    *   `webdriver-manager`: For automatic management of browser drivers (e.g., ChromeDriver).
    *   `BeautifulSoup4`: For parsing HTML content extracted by Selenium.
*   **AI & Machine Learning:**
    *   `google-generativeai`: Official Google AI SDK for Python to interact with Gemini models.
    *   **AI Model:** Google Gemini 2.0 Flash.
*   **Database:**
    *   `sqlite3`: Python's built-in module for SQLite database interaction.
*   **CLI Development:**
    *   `argparse` (or `click`, as implemented): For creating the command-line interface.
*   **Configuration & Utilities:**
    *   `python-dotenv`: For managing environment variables (like API keys).
    *   `getpass`: For secure input of passwords via the CLI.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Python:** Version 3.9 or higher.
*   **Git:** For cloning the repository.
*   **Web Browser:** A modern web browser supported by Selenium (e.g., Google Chrome, Mozilla Firefox).
*   **Google Cloud Project & Gemini API Key:** You will need an active Google Cloud project with the Generative Language API enabled and a valid API key for Gemini. You can obtain this from the [Google AI Studio](https://aistudio.google.com/) or Google Cloud Console.

## Setup & Installation

1.  **Clone the Repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone https://github.com/MasuRii/FBScrapeIdeas.git
    ```

2.  **Navigate to the Project Directory:**
    ```bash
    cd FBScrapeIdeas 
    ```
    *(Adjust `FBScrapeIdeas` if your local directory name is different)*

3.  **Create and Activate a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.

    *   **Linux/macOS (bash/zsh):**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

    *   **Windows (Command Prompt):**
        ```bash
        python -m venv venv
        venv\Scripts\activate.bat
        ```

    *   **Windows (PowerShell):**
        ```powershell
        python -m venv venv
        .\venv\Scripts\Activate.ps1 
        ```
        *(You might need to set execution policy: `Set-ExecutionPolicy Unrestricted -Scope Process`)*

4.  **Install Dependencies:**
    With your virtual environment activated, install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up Environment Variables:**
    This project uses a `.env` file to store sensitive information like API keys and Facebook credentials.
    *   Create a file named `.env` in the root of the project directory.
    *   Add your Google Gemini API key and Facebook credentials to this file. You can use the `.env.example` file (if provided in the repository) as a template:
        ```dotenv
        # .env
        GOOGLE_API_KEY=YOUR_GEMINI_API_KEY_HERE
        FB_USER=YOUR_FACEBOOK_EMAIL_OR_USERNAME
        FB_PASS=YOUR_FACEBOOK_PASSWORD
        ```
    **Important:** The `.env` file should be listed in your `.gitignore` file to prevent accidental commitment of sensitive credentials.

6.  **WebDriver Setup:**
    The `webdriver-manager` library, included in `requirements.txt`, will attempt to automatically download and manage the correct WebDriver for your installed browser (e.g., ChromeDriver for Chrome) the first time the scraper is run. Ensure you have the browser itself installed.

## Configuration

Key configurations for the application are managed as follows:

*   **Google Gemini API Key:** Set in the `.env` file as `GOOGLE_API_KEY`.
*   **Facebook Credentials:** Set in the `.env` file as `FB_USER` and `FB_PASS`. These are read at runtime for scraping and are **not** stored persistently by the application beyond the current session.
    *Alternatively, if `.env` entries are not found, the `scrape` command will securely prompt for Facebook credentials using `getpass`.*
*   **AI Categories & Prompt:**
    *   The predefined categories for AI classification are defined within the `response_schema` used when calling the Gemini API, typically found in `ai/gemini_service.py` or a related schema definition file (e.g., `ai/gemini_schema.json`).
    *   The main prompt instructing the Gemini model is also located within `ai/gemini_service.py`.
    Developers can inspect or modify these directly in the code for custom behavior.
*   **Scraping Targets:**
    *   **Facebook Group URL:** Provided as a command-line argument (`--group-url`) to the `scrape` command.
    *   **Number of Posts:** Optionally specified via the `--num-posts` argument to the `scrape` command.

## Usage (CLI Commands)

The application is operated through its command-line interface. The general syntax is:

```bash
python main.py <command> [options]
```

### `scrape`

*   **Purpose:** Initiates the process of scraping posts from a specified Facebook group.
*   **Syntax:**
    ```bash
    python main.py scrape --group-url <FACEBOOK_GROUP_URL> [--num-posts <NUMBER>] [--headless]
    ```
*   **Options:**
    *   `--group-url <URL>`: (Required) The full URL of the Facebook group to scrape.
    *   `--num-posts <NUMBER>`: (Optional) The maximum number of posts to attempt to scrape. Defaults to a predefined value if not specified.
    *   `--headless`: (Optional) Runs the Selenium-controlled browser in headless mode (without a visible UI). Useful for servers or automated runs.
*   **Behavior:**
    *   Reads Facebook credentials from the `.env` file. If not found, it will securely prompt for your Facebook email/username and password.
    *   Launches a browser, logs into Facebook, navigates to the group, and scrapes posts.
    *   Saves scraped data to the `insights.db` SQLite database.
*   **Example:**
    ```bash
    python main.py scrape --group-url "https://www.facebook.com/groups/your_target_group_id" --num-posts 50 --headless
    ```

### `process-ai`

*   **Purpose:** Processes posts stored in the database that have not yet been categorized by the AI.
*   **Syntax:**
    ```bash
    python main.py process-ai
    ```
*   **Behavior:**
    *   Fetches posts from `insights.db` where `is_processed_by_ai` is `0` and `post_content_raw` is not null.
    *   Sends these posts in batches to the Google Gemini 2.0 Flash API for categorization using the configured prompt and schema.
    *   Updates the database records with the AI-generated category, summary, keywords, etc.
*   **Example:**
    ```bash
    python main.py process-ai
    ```

### `view`

*   **Purpose:** Displays categorized posts from the SQLite database in the console.
*   **Syntax:**
    ```bash
    python main.py view [--category <CATEGORY_NAME>] [--limit <NUMBER>]
    ```
*   **Options:**
    *   `--category <CATEGORY_NAME>`: (Optional) Filters the displayed posts to only show those matching the specified category (e.g., "Project Idea").
    *   `--limit <NUMBER>`: (Optional) Limits the number of posts displayed.
*   **Example:**
    ```bash
    # View all categorized posts (default limit may apply)
    python main.py view

    # View up to 10 posts categorized as 'Project Idea'
    python main.py view --category "Project Idea" --limit 10
    ```

### Getting Help

To see a list of all commands or get help for a specific command, use the `--help` flag:

```bash
python main.py --help
python main.py scrape --help
python main.py process-ai --help
python main.py view --help
```

## Project Structure

A brief overview of the project's directory layout:

```
FBScrapeIdeas/
├── .env                # Local environment variables (API keys, credentials - Git ignored)
├── .env.example        # Example template for .env file
├── .gitignore          # Specifies intentionally untracked files that Git should ignore
├── README.md           # This documentation file
├── requirements.txt    # Python package dependencies
├── main.py             # CLI entry point and command definitions
├── ai/
│   ├── __init__.py
│   ├── gemini_service.py # Logic for interacting with Gemini API, batching, prompting
│   └── (gemini_schema.json) # Optional: If schema is in a separate JSON file
├── database/
│   ├── __init__.py
│   ├── crud.py           # Functions for database Create, Read, Update operations
│   └── db_setup.py       # Script to initialize database schema
├── scraper/
│   ├── __init__.py
│   ├── facebook_scraper.py # Core Selenium logic for login and post scraping
│   └── (webdriver_setup.py) # Potentially separate WebDriver initialization logic
└── insights.db         # SQLite database file (created on first run/setup)
```

## Ethical Considerations & Limitations

*   **Ethical Use & Terms of Service:** Users are solely responsible for ensuring their use of this tool complies with Facebook's Terms of Service, the rules of any specific group being scraped, and all applicable data privacy laws and regulations. This tool is intended for personal research or academic purposes.
*   **Credential Security:**
    *   Facebook credentials provided in the `.env` file or via CLI prompt are used for the duration of the scraping session only and are **not** stored persistently by the application in any recoverable format after the session ends.
    *   However, using personal credentials with automated tools carries inherent security risks. Exercise caution and consider the security implications.
*   **Facebook UI Changes:** Facebook frequently updates its website structure. These changes can break the Selenium selectors used for scraping, requiring code updates to maintain functionality. This is an ongoing maintenance consideration.
*   **Two-Factor Authentication (2FA):** If 2FA is enabled on the Facebook account used for scraping, manual intervention (e.g., entering a code) may be required during the automated login process. The current MVP does not fully automate 2FA.
*   **`posted_at` Timestamp Accuracy:** Observations indicate that the parsing of relative Facebook timestamps (e.g., "2 hours ago") might occasionally result in dates set to the current year but with future month/day or default to midnight. If high precision for post timestamps is critical, this date parsing logic may require further refinement.
*   **Rate Limiting & Anti-Scraping:** Extensive or rapid scraping could trigger Facebook's anti-scraping measures or rate limits, potentially leading to temporary blocks or CAPTCHAs. The tool implements basic waits but does not include advanced anti-detection techniques.

## Future Enhancements (Roadmap)

Potential areas for future development include:

*   Support for scraping and managing multiple Facebook groups.
*   User-configurable AI categories and more dynamic prompt management.
*   Development of a web-based user interface (UI) for easier interaction.
*   Implementation of scheduled/automated scraping and AI processing tasks.
*   Advanced filtering, searching, and analytical capabilities within the application.
*   Improved accuracy and robustness of `posted_at` date/time parsing.
*   More sophisticated error handling and recovery for scraping interruptions.
