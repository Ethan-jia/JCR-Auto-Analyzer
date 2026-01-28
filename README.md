# 🕸️ JCR Auto-Analyzer (The Iron Spider)

> An automated Python tool to scrape JCR (Journal Citation Reports) rankings, Quartiles, and Index status (SCIE/SSCI).
> Designed to help researchers efficiently filter journals based on university publishing requirements (e.g., Q1/Q2 + SCIE/SSCI).

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![DrissionPage](https://img.shields.io/badge/Powered%20By-DrissionPage-green) ![License](https://img.shields.io/badge/License-MIT-orange)

## 🚀 Features

* **Auto-Login Support**: Automatically detects USM (Universiti Sains Malaysia) campus network to skip login.
* **Smart Filtering**: Fetches `Rank`, `Quartile`, `SCIE/SSCI` status.
* **Excel Report**: Generates a clean `.xlsx` report sorted by "Pass/Fail" based on requirements.
* **Anti-Detection**: Uses `DrissionPage` to simulate real user behavior.
* **Fail-Fast Mechanism**: Auto-detects network issues or browser crashes to save resources.

## 📦 Installation

1. Clone the repo:
   ```bash
   git clone [https://github.com/YourUsername/JCR-Auto-Analyzer.git](https://github.com/YourUsername/JCR-Auto-Analyzer.git)
   cd JCR-Auto-Analyzer

2. Install dependencies:	

   ```bash
   pip install pandas DrissionPage loguru openpyxl
   ```

## 🛠️ Usage

1. **Configure**: Open `jcr_tool.py` and set your `CHROME_PATH`.

2. **Prepare Data**: Place your Excel file (must have `eISSN` and `Journal Title` columns) in the folder.

3. **Run**:

   ```bash
   python jcr_tool.py
   ```

4. **Result**: Check the `downloads` folder for the analyzed report.

## ⚠️ Important Note

- **Network Access**: Access to JCR requires an institutional subscription (IP-based). Ensure you are connected to your university WiFi or VPN.
- **Disclaimer**: This tool is for **educational and research purposes only**. Please respect Clarivate's Terms of Service. Do not use this for commercial bulk scraping.

## 👨‍💻 Author

**Ethan** *USM Research Group*

------

*"Code is like humor. When you have to explain it, it’s bad."*