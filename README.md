# Send Developing Letters Automator

## Description

This project automates the process of generating personalized business development emails. It reads target company data from an Excel file, fetches website content, uses the DeepSeek API to extract business descriptions and identify cooperation points, generates a tailored email body and subject, selects relevant images, and saves the complete email as a draft in Gmail.

## Features

* Reads target company information (website, email, contact) from an Excel file.
* Scrapes website content for analysis.
* Utilizes DeepSeek API for:
    * Extracting main business descriptions.
    * Identifying cooperation points between your company and the target.
    * Generating personalized email drafts (subject and HTML body).
* Selects relevant local images based on email content and company name.
* Creates MIME email messages with inline images and attachments.
* Authenticates with Gmail using OAuth 2.0.
* Saves generated emails as drafts in the specified Gmail account.
* Logs processing steps and errors to console and dated log files.
* Saves processed data (including generated content and status) to an output Excel file.
* Configurable via `.env` (for secrets) and `config.ini` (for settings/paths).
* Modular code structure for better maintainability.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd Send_Developing_Letters
    ```

2.  **Install dependencies using Poetry:**
    (Ensure you have Python 3.9+ and Poetry installed: https://python-poetry.org/docs/#installation)
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all necessary packages based on `poetry.lock`.

## Configuration

This project uses two configuration files located in the project root:

1.  **`.env` file (Secrets & Environment Specifics)**
    * **IMPORTANT:** This file contains sensitive information and **must NOT be committed to Git**. Make sure it is listed in your `.gitignore` file.
    * Create a file named `.env` in the project root.
    * Copy the structure from the example below and fill in your actual credentials and paths.

    ```dotenv
    # .env - Example Structure (DO NOT COMMIT ACTUAL VALUES)

    # --- Secrets ---
    DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

    # --- Gmail/Email Account ---
    SENDER_EMAIL=your_gmail_address@gmail.com

    # --- Credential Paths (Relative to Project Root) ---
    # Path to the downloaded credentials.json from Google Cloud Console
    GMAIL_CREDENTIALS_PATH=credentials/credentials.json
    # Path where the generated token.json will be stored (leave as default unless needed)
    GMAIL_TOKEN_PATH=token.json

    # --- Environment Specific (Optional) ---
    # LOG_LEVEL=DEBUG
    ```

2.  **`config.ini` file (Application Settings & Paths)**
    * This file contains non-secret configuration like file paths relative to the project root and application behavior settings.
    * Create a file named `config.ini` in the project root.
    * Use the structure below and adjust paths and settings as needed for your project layout.

    ```ini
    # config.ini - Example Structure

    [PATHS]
    skyfend_business_doc = data/raw/test_main Business of Skyfend.docx
    company_data_excel = data/raw/test_to_read_website.xlsx
    processed_data_excel = data/processed/saving_company_data_after_creating_letters.xlsx
    product_brochure_pdf = data/raw/files/1.Product brochure of Skyfend.pdf
    unified_images_dir = data/raw/image_unified/
    log_dir = logs/

    [EMAIL_DEFAULTS]
    max_images_per_email = 3

    [APP_SETTINGS]
    log_level = INFO # Default log level (can be overridden by .env)

    [WEBSITE_SCRAPER]
    max_content_length = 3000
    timeout = 20

    [API_CLIENT]
    request_timeout = 45
    ```

3.  **Gmail API Credentials (`credentials.json`)**
    * You need to enable the Gmail API in your Google Cloud Console project.
    * Create OAuth 2.0 Client ID credentials for a "Desktop app".
    * Download the credentials JSON file.
    * Save the downloaded file to the path specified in `GMAIL_CREDENTIALS_PATH` within your `.env` file (e.g., create a `credentials/` directory in your project root and save it there as `credentials.json`).

## Usage

1.  **Prepare Data:**
    * Ensure your target company data is correctly formatted in the Excel file specified by `company_data_excel` in `config.ini`. Include columns like `Company`, `Website`, `Recipient_Email`, `Contact Person`, and a `Process` column ('yes'/'no').
    * Place your company's business description document at the path specified by `skyfend_business_doc`.
    * Place the product brochure PDF at the path specified by `product_brochure_pdf`.
    * Place images ready for emailing in the directory specified by `unified_images_dir`.

2.  **Run the script:**
    Activate the virtual environment managed by Poetry and run the main script:
    ```bash
    poetry run python src/main.py
    ```

3.  **Gmail Authorization (First Run):**
    The first time you run the script, it will likely open a browser window asking you to log in to your Google account (the `SENDER_EMAIL`) and authorize the application to access Gmail (to create drafts). Follow the prompts. A `token.json` file (or the path specified in `GMAIL_TOKEN_PATH`) will be created to store the authorization for future runs.

4.  **Output:**
    * Processing logs will be printed to the console and saved to a dated file in the `logs/` directory.
    * Generated emails will be saved as drafts in the specified Gmail account.
    * A summary of processed companies, generated content, and status will be saved to the Excel file specified by `processed_data_excel`.

## Project Structure