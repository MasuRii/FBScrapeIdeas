# University Group Insights Platform

## Overview
This tool is a CLI-driven application designed to scrape posts from a specified university Facebook group (requiring user-provided credentials for authenticated access via Selenium). It then uses Google's Gemini 2.0 Flash for GenAI categorization of these posts via batch processing and structured JSON outputs, and stores them in a SQLite database to identify potential capstone/thesis ideas, student problems, or other insights.

**Problem Statement:** Manually sifting through numerous Facebook group posts, especially those requiring login, to find relevant ideas, problems, or trends is time-consuming and inefficient. Potential valuable insights for academic projects or understanding student needs can be easily missed.

**Target Audience:** Primarily students looking for capstone/thesis ideas, researchers, or university faculty/staff interested in understanding student concerns and interests.

**Value Proposition:** Automates the discovery and categorization of student-generated ideas and problems from a university Facebook group, including those requiring authenticated access. Saves time and surfaces valuable insights for academic and research purposes by leveraging advanced AI (Gemini 2.0 Flash) for efficient, structured processing.

## Goals & Objectives
*   Successfully scrape relevant posts (content, URL, timestamp) from the target Facebook group using Selenium and user-provided credentials.
*   Accurately categorize posts using Gemini 2.0 Flash based on predefined themes (e.g., "problem statement," "project idea"), utilizing structured JSON output.
*   Efficiently process posts by batching them for the Gemini API.
*   Store scraped and categorized posts in a structured SQLite database for easy querying and review via CLI.
*   Provide CLI commands to trigger scraping, AI processing, and viewing of posts.

## Core Features

*   **Facebook Group Scraper (Authenticated):** Uses Selenium and user-provided Facebook credentials to scrape post content, URLs, and timestamps from a specified group. It handles login and navigation to collect data from groups requiring authentication.
*   **GenAI Post Categorization (Gemini 2.0 Flash):** Integrates with Google's Gemini 2.0 Flash model to analyze scraped post text and categorize them based on predefined themes (like "problem statement" or "project idea"). It processes posts in batches for efficiency and outputs structured JSON.
*   **Database Storage & Retrieval (SQLite):** Stores scraped posts and their AI-generated categorizations in a local SQLite database (`insights.db`) for persistent storage and easy access. Includes functions to add new posts, update with AI results, and retrieve data.
*   **CLI Interface:** Provides a command-line interface for users to trigger scraping, initiate AI processing, and view categorized posts with optional filtering.

## Technology Stack

*   **Programming Language:** Python
*   **Scraping:** `Selenium`, `webdriver-manager`, `BeautifulSoup4`
*   **GenAI Integration:** `google-generativeai` (Google AI SDK for Python)
*   **AI Model:** Google Gemini 2.0 Flash
*   **Database:** `sqlite3`
*   **CLI:** `argparse` (or `click`)
*   **Configuration:** `python-dotenv`
*   **Credential Input:** `getpass`

## Setup & Installation

Follow these steps to set up the project and install dependencies:

### Prerequisites

*   **Python:** Ensure you have Python (version 3.9+ recommended) installed.
*   **Git:** You need Git to clone the repository.
*   **Web Browser:** A compatible web browser (like Google Chrome) is required for Selenium.
*   **Google AI Studio & Gemini API Key:** Obtain a Gemini API key from Google AI Studio.

### Steps

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/MasuRii/FBScrapeIdeas
    ```

2.  **Navigate to the Project Directory:**

    ```bash
    cd <repository_name>
    ```

3.  **Create and Activate a Virtual Environment:**

    *   **Linux/macOS (bash/zsh):**

        ```bash
        python -m venv venv
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
        venv\Scripts\Activate.ps1
        ```

4.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Set up Environment Variables:**

    Create a file named `.env` in the root of the project directory. Add your Google Gemini API key to this file in the following format:

    ```
    GOOGLE_API_KEY=<Your_Gemini_API_Key>
    ```

    *(Note: The `.env` file is ignored by Git for security.)*

6.  **WebDriver Setup:**

    The `webdriver-manager` library will automatically download the necessary WebDriver for your installed browser when the script is run. Ensure your chosen browser (e.g., Chrome) is installed on your system.

## Configuration Details

*   **Gemini API Key:** Your Google Gemini API key needs to be set in a `.env` file in the root directory of the project, like this:

    ```
    GOOGLE_API_KEY=<Your_Gemini_API_Key>
    ```

    *(Note: A `.env.example` file is provided as a template, and the `.env` file is ignored by Git for security.)*
*   **Facebook Credentials:** Your Facebook email/username (`FB_USER`) and password (`FB_PASS`) should also be added to the `.env` file:

    ```
    FB_USER=<Your_Facebook_Email_or_Username>
    FB_PASS=<Your_Facebook_Password>
    ```

    *(Note: These credentials are read at runtime for scraping and are NOT stored persistently by the application.)*
*   **AI Categories:** The predefined categories used for AI categorization are currently defined within the code (e.g., in `ai/gemini_service.py` or referenced by `ai/gemini_schema.json`). Developers can inspect or modify these directly in the code if needed.
*   **Gemini Prompt:** The prompt used to instruct the Gemini model is located within `ai/gemini_service.py`. Developers can inspect or tweak this prompt for different categorization behavior.
*   **Facebook Group URL & Number of Posts:** These primary configurations for scraping are provided as command-line arguments when running the `scrape` command.

## Usage

This application is run via the command line. The general execution pattern is:

```bash
python main.py <command> [options]
```

Here are the available commands:

### `scrape`

*   **Purpose:** Scrape posts from a specified Facebook group.
*   **Syntax:**

    ```bash
    python main.py scrape --group-url <FACEBOOK_GROUP_URL> [--num-posts <NUMBER>] [--headless]
    ```
*   **Explanation:** This command initiates the scraping process. You must provide the URL of the Facebook group using the `--group-url` option. The script will prompt you securely for your Facebook email/username and password using `getpass`. The optional `--num-posts` argument allows you to specify the maximum number of posts to attempt to scrape. The optional `--headless` flag allows you to run the browser without a graphical user interface.
*   **Example:**

    ```bash
    python main.py scrape --group-url https://www.facebook.com/groups/your_group_id --num-posts 100
    ```

### `process-ai`

*   **Purpose:** Categorize unprocessed posts in the database using Google's Gemini 2.0 Flash model.
*   **Syntax:**

    ```bash
    python main.py process-ai
    ```
*   **Explanation:** This command fetches posts from the SQLite database that have not yet been processed by the AI (`is_processed_by_ai` is 0), sends them in batches to the Gemini API for categorization, and updates the database with the AI results. Ensure your `GOOGLE_API_KEY` is set in the `.env` file.
*   **Example:**

    ```bash
    python main.py process-ai
    ```

### `view`

*   **Purpose:** Display categorized posts stored in the SQLite database.
*   **Syntax:**

    ```bash
    python main.py view [--category <CATEGORY_NAME>]
    ```
*   **Explanation:** This command retrieves and displays posts from the database. You can optionally filter the results by providing a specific category name using the `--category` option.
*   **Example:**

    ```bash
    # View all categorized posts
    python main.py view

    # View posts categorized as 'project idea'
    python main.py view --category "project idea"
    ```

For more details on command options, use the `--help` flag:

```bash
python main.py --help
python main.py <command> --help
```

## Project Structure Overview

Here is a more detailed representation of the project's directory structure and the purpose of key files and folders:

*   `FBScrapeIdeas/`:
        *   `ai/`:
            *   `gemini_schema.json`: JSON schema for Gemini output.
            *   `gemini_service.py`: Logic for interacting with the Gemini API.
        *   `database/`:
            *   `crud.py`: Database Create, Read, Update, Delete operations.
            *   `db_setup.py`: Script for setting up the SQLite database.
        *   `scraper/`:
            *   `auth_handler.py`: Handles Facebook authentication.
            *   `facebook_scraper.py`: Contains the core scraping logic using Selenium.
            *   `webdriver_setup.py`: Manages the Selenium WebDriver.
        *   `config.py`: Configuration file for the application.
        *   `insights.db`: The SQLite database file (generated).
        *   `main.py`: The main command-line interface entry point.
        *   `README.md`: Project documentation.
        *   `requirements.txt`: Lists project dependencies.
        *   `.env` / `.env.example`: Used for managing environment variables.
        *   `.gitignore`: Specifies intentionally untracked files.

## Ethical Considerations & Limitations

*   **Ethical Use:** Users are responsible for adhering to Facebook's Terms of Service, group rules, and data privacy principles when using this tool. This tool is intended for personal or research use, and user-provided credentials should be handled with care. The application does *not* store your Facebook credentials persistently.
*   **Facebook Scraping Instability:** Facebook's user interface changes frequently. Updates to their HTML structure can break the Selenium-based scraper, requiring updates to the element selectors in the code.
*   **Credential Security:** While the application does not store credentials, using automated tools with your Facebook login carries inherent risks. Use with caution and understand the implications.
*   **Two-Factor Authentication (2FA):** If 2FA is enabled on your Facebook account, manual intervention may be required during the login process when running the scraper.
*   **`posted_at` Accuracy:** There is an observed limitation where the parsing of relative Facebook timestamps might occasionally result in future dates or midnight times. If high precision for post timestamps is critical for your use case, this aspect may require future refinement.

## Future Enhancements (Roadmap)

Here are some potential future enhancements for the project:

*   Support for scraping multiple groups.
*   User-defined categories and more sophisticated prompt management for Gemini.
*   Web interface.
*   Scheduled/automated scraping and processing.
*   Advanced filtering/searching based on AI-extracted keywords and summaries.
*   Refinement of `posted_at` date/time parsing for higher accuracy. 