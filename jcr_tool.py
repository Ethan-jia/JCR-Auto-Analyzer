# -*- coding: utf-8 -*-
"""
==============================================================================
   JCR JOURNAL ANALYZER TOOL
==============================================================================
   
   Author  : Ethan
   Created : 2026-01
   For     : Gobithaasan Rudrusamy Research Group (USM)
   
   [Description]
   This tool automatically scrapes JCR rankings, Quartiles, and Index status 
   (SCIE/SSCI). It helps researchers filter eligible journals based on 
   University requirements (Q1/Q2 + SCIE/SSCI).

   [Feature: Auto-Login]
   This script is optimized for the USM Network. It will AUTOMATICALLY SKIP 
   the JCR login page if you are connected to the campus network.

   [Usage]
   1. Pip install requirements: pandas, DrissionPage, loguru, openpyxl
   2. Set your Chrome path in the CONFIG section below.
   3. Prepare your Excel file.
   4. Run!
   
   [!!! CRITICAL REQUIREMENT !!!]
   USM CAMPUS NETWORK REQUIRED: 
   > Please verify your USM WiFi connection immediately.

   "Code is like humor. When you have to explain it, it's bad."
   
==============================================================================
"""

import os
import sys
import time
import json
import glob
import pandas as pd
from DrissionPage import WebPage, ChromiumOptions
from DrissionPage.common import Keys
from loguru import logger

# ==========================================
#      USER CONFIGURATION (SETTINGS)
# ==========================================

# Path to your Google Chrome Application
# [Mac Example]: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
# [Win Example]: r'C:\Program Files\Google\Chrome\Application\chrome.exe'
CHROME_PATH = ''

# Input Excel Settings (Must be in the same folder as this script)
# Name of your raw excel file
INPUT_EXCEL_NAME = ''

# Header Row Index (0-based)
# If the Excel has a logo/title in the first 5 rows, the real header is on Row 6.
# So set this to 5. (If it starts on Row 1, set to 0).
EXCEL_HEADER_ROW = 5

# Filter specific discipline? (Set None to process all rows)
# Please copy from the Subject Area column in the Excel spreadsheet.
# Example: "Computer Science" or None
TARGET_DISCIPLINE = None

# Background Mode
# True = Invisible / False = Visible for debugging
HEADLESS_MODE = True

# Output Paths
OUTPUT_DIR = "downloads"
LOG_DIR = "logs"


#  本地保留原始内容（不修改你的本地文件）
#  git config filter.local-config.smudge 'cat'
# ==========================================
CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
INPUT_EXCEL_NAME = 'Eligible+journals.xlsx'
HEADLESS_MODE = False
# LOCAL_CONFIG_END


# ==========================================
#           SYSTEM INIT
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, INPUT_EXCEL_NAME)
USER_DATA_PATH = os.path.join(BASE_DIR, '.chrome_user_data')
OUTPUT_PATH = os.path.join(BASE_DIR, OUTPUT_DIR)
LOG_PATH = os.path.join(BASE_DIR, LOG_DIR)
TIMESTAMP = time.strftime('%Y%m%d_%H%M%S')
RESULT_JSONL = os.path.join(OUTPUT_PATH, f"jcr_raw_{TIMESTAMP}.jsonl")

for d in [USER_DATA_PATH, OUTPUT_PATH, LOG_PATH]:
    os.makedirs(d, exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(os.path.join(LOG_PATH, "spider_{time}.log"),
           rotation="10 MB", retention="7 days", encoding="utf-8")

# ==========================================
#           MODULE 1: SPIDER
# ==========================================


class BrowserEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserEngine, cls).__new__(cls)
            cls._instance.page = None
        return cls._instance

    def start(self):
        if self.page:
            return self.page
        co = ChromiumOptions()
        if os.path.exists(CHROME_PATH):
            co.set_paths(browser_path=CHROME_PATH)
        co.set_user_data_path(USER_DATA_PATH)
        co.set_argument('--window-size=1920,1080')
        co.set_argument('--no-imgs')
        co.set_argument('--mute-audio')
        if HEADLESS_MODE:
            co.headless(True)

        try:
            self.page = WebPage(chromium_options=co)
            logger.success(">>> Browser Started Successfully")
            return self.page
        except Exception as e:
            logger.critical(f"Browser Init Failed: {e}")
            sys.exit(1)


def load_tasks():
    if not os.path.exists(EXCEL_PATH):
        logger.error(f"Input file not found: {EXCEL_PATH}")
        return []
    try:
        logger.info(
            f"Reading Excel: {INPUT_EXCEL_NAME} (Header at row {EXCEL_HEADER_ROW+1})...")
        df = pd.read_excel(EXCEL_PATH, header=EXCEL_HEADER_ROW)
        df.columns = df.columns.astype(str).str.strip()

        required_cols = ['eISSN', 'Journal Title', 'Main Discipline']
        for col in required_cols:
            if col not in df.columns:
                logger.error(
                    f"❌ Missing column: '{col}'. Found: {df.columns.tolist()}")
                return []

        if TARGET_DISCIPLINE:
            mask = (df['Main Discipline'].astype(str).str.strip()
                    == TARGET_DISCIPLINE) & (df['eISSN'].notna())
            target_rows = df[mask].copy()
        else:
            target_rows = df[df['eISSN'].notna()].copy()

        tasks = target_rows[['eISSN', 'Journal Title']].to_dict('records')
        logger.info(f"✅ Successfully loaded {len(tasks)} tasks.")
        return tasks
    except Exception as e:
        logger.error(f"Error reading Excel: {e}")
        return []


def save_raw_data(data):
    try:
        with open(RESULT_JSONL, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.error(f"Save failed: {e}")


def extract_jcr_details(tab):
    data = {"jcr_rankings": [], "editions": [],
            "is_scie": False, "is_ssci": False}

    try:
        container = tab.wait.ele_displayed(
            'css:.incites-jcr3-fe-rank-by-jif', timeout=8)
    except:
        return data

    if not container:
        return data

    edition_eles = container.eles('css:.edition-value')
    for ed in edition_eles:
        txt = ed.text.strip()
        if txt:
            data["editions"].append(txt)
            if "Science Citation Index Expanded" in txt or "SCIE" in txt:
                data["is_scie"] = True
            if "Social Sciences Citation Index" in txt or "SSCI" in txt:
                data["is_ssci"] = True

    slides = container.eles('css:.slide-cell')
    for slide in slides:
        cat_ele = slide.ele('css:.category-value')
        if not cat_ele:
            continue

        category_data = {"category": cat_ele.text, "history": []}
        rows = slide.eles('tag:tr')

        for row in rows:
            year_ele = row.ele('css:.rbj-year')
            if year_ele and "JCR YEAR" not in year_ele.text:
                rank_ele = row.ele('css:.rbj-rank')
                q_ele = row.ele('css:.rbj-quartile')

                category_data["history"].append({
                    "year": year_ele.text,
                    "rank": rank_ele.text if rank_ele else "N/A",
                    "quartile": q_ele.text if q_ele else "N/A"
                })
        data["jcr_rankings"].append(category_data)

    return data


def close_cookie_popup(page):
    try:
        btn = page.ele(
            'tag:button@class:onetrust-close-btn-handler', timeout=2)
        if btn:
            btn.click()
            time.sleep(0.5)
    except:
        pass


def get_completed_issns():
    completed = set()
    files = glob.glob(os.path.join(OUTPUT_PATH, '*.jsonl'))
    logger.info(f"📂 Scanning {len(files)} history files for resume...")

    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            issn = data.get('issn')
                            if issn:
                                completed.add(str(issn).strip())
                        except:
                            pass
        except Exception:
            pass
    return completed


def run_spider():
    all_tasks = load_tasks()

    if not all_tasks:
        logger.warning("⚠️ No tasks to process (Check Excel file or Filter).")
        logger.info("🛑 Exiting script now...")

        sys.exit(0)

    completed_issns = get_completed_issns()

    tasks_to_do = [t for t in all_tasks if t['eISSN'] not in completed_issns]
    skipped_count = len(all_tasks) - len(tasks_to_do)

    if skipped_count > 0:
        logger.success(
            f"⏭️  Auto-Resume: Skipped {skipped_count} already downloaded journals.")

    if not tasks_to_do:
        logger.success(
            "🎉 All tasks are already completed! Going straight to Analysis.")
        return

    logger.info(
        f"🚀 Starting Spider for remaining {len(tasks_to_do)} journals...")

    engine = BrowserEngine()
    page = engine.start()
    home_url = "https://jcr.clarivate.com/jcr/home"

    logger.info(">>> Opening JCR Homepage...")
    page.get(home_url)

    logger.warning(
        "⚠️  [CHECK NETWORK] Are you on USM WiFi? JCR requires institutional access.")
    time.sleep(15)

    close_cookie_popup(page)

    total = len(tasks_to_do)
    for idx, task in enumerate(tasks_to_do):
        issn = task.get("eISSN")
        title = task.get("Journal Title")
        logger.info(f"[{idx+1}/{total}] Processing: {title} ({issn})")

        try:

            if not page.url:
                raise Exception("Browser disconnected")

            while page.tabs_count > 1:
                page.latest_tab.close()
            page.get(home_url)

            search_input = page.wait.ele_displayed(
                'css:input[type="text"]', timeout=15)
            if not search_input:
                logger.critical("🚨 FATAL ERROR: Search bar not found!")
                logger.critical("👉 This usually means you are NOT logged in.")
                logger.critical(
                    "🛑 Stopping script to prevent further errors. Please check your USM WiFi.")
                try:
                    page.quit()
                except:
                    pass
                sys.exit(1)  # <--- Force Quit Here

            search_input.click()
            time.sleep(0.5)
            page.actions.key_down(Keys.COMMAND).type(
                'a').key_up(Keys.COMMAND).type(Keys.BACKSPACE)
            search_input.input(issn)

            try:
                page.wait.ele_displayed(
                    '.popup-box .ng-star-inserted', timeout=6)
                page.actions.type(Keys.ENTER)
            except:
                page.actions.type(Keys.ENTER)

            first_row = page.wait.ele_displayed('@class:mat-row', timeout=8)
            if not first_row:
                logger.warning(f"No result found for {issn}")
                save_raw_data(
                    {"issn": issn, "journal_name": title, "status": "Not Found"})
                continue

            first_row.ele('@class:table-cell-journalName').click()
            page.wait.new_tab(timeout=10)
            new_tab = page.latest_tab

            if new_tab.wait.ele_displayed('text:Rank by Journal Impact Factor', timeout=15):
                new_tab.scroll.down(600)
                time.sleep(1)

                extracted = extract_jcr_details(new_tab)
                record = {
                    "issn": issn,
                    "journal_name": title,
                    "scie_check": extracted["is_scie"],
                    "ssci_check": extracted["is_ssci"],
                    "rankings": extracted["jcr_rankings"],
                    "status": "Success"
                }
                save_raw_data(record)

                idx_status = []
                if extracted["is_scie"]:
                    idx_status.append("SCIE")
                if extracted["is_ssci"]:
                    idx_status.append("SSCI")
                logger.success(
                    f"Captured: {', '.join(idx_status) if idx_status else 'None'}")
            else:
                logger.error("Details page timeout.")
                save_raw_data(
                    {"issn": issn, "journal_name": title, "status": "Timeout"})

            new_tab.close()

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Error occurred: {err_msg}")

            if "断开" in err_msg or "disconnected" in err_msg or "closed" in err_msg or "target window already closed" in err_msg:
                logger.critical(
                    "🚨 BROWSER CONNECTION LOST! Aborting script to prevent infinite errors.")
                logger.critical(
                    "👉 Possible reasons: Chrome closed manually / Driver mismatch / RAM full.")
                logger.critical(
                    "💡 Suggestion: Try closing all Google Chrome windows, then reopen the terminal and run the script.")
                try:
                    page.quit()
                except:
                    pass
                sys.exit(1)

    if page:
        try:
            page.quit()
        except:
            pass
    logger.success(">>> Spider Task Completed.")

# ==========================================
#           MODULE 2: ANALYZER
# ==========================================


def run_analysis():
    logger.info(">>> Starting Data Analysis...")

    files = glob.glob(os.path.join(OUTPUT_PATH, '*.jsonl'))
    if not files:
        logger.error("No data files found.")
        return

    target_file = max(files, key=os.path.getctime)
    output_excel = target_file.replace('.jsonl', '_Report.xlsx')

    excel_rows = []
    quartile_map = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4, 'N/A': 99}

    with open(target_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except:
                continue

            is_scie = rec.get('scie_check', False)
            is_ssci = rec.get('ssci_check', False)

            indexes = []
            if is_scie:
                indexes.append("SCIE")
            if is_ssci:
                indexes.append("SSCI")
            index_str = " + ".join(indexes) if indexes else "None"

            best_q = "N/A"
            best_score = 99
            best_year = "N/A"
            best_rank = "N/A"
            cats = []

            for cat in rec.get('rankings', []):
                cats.append(cat['category'])
                hist = cat.get('history', [])
                if not hist:
                    continue

                latest = hist[0]
                if "JCR YEAR" in latest['year'] and len(hist) > 1:
                    latest = hist[1]

                q = latest.get('quartile', 'N/A')
                score = quartile_map.get(q, 99)

                if score < best_score:
                    best_score = score
                    best_q = q
                    best_year = latest.get('year')
                    best_rank = latest.get('rank')

            is_high_tier = best_q in ['Q1', 'Q2']
            is_indexed = is_scie or is_ssci

            if is_high_tier and is_indexed:
                usm_status = "✅ PASS"
            elif not is_indexed:
                usm_status = "❌ Not Indexed"
            else:
                usm_status = "⚠️ Q3/Q4"

            excel_rows.append({
                "Journal Title": rec.get('journal_name'),
                "ISSN": rec.get('issn'),
                "USM Requirement": usm_status,
                "Best Quartile": best_q,
                "Indexes": index_str,
                "Rank": best_rank,
                "Year": best_year,
                "Categories": " | ".join(cats),
                "Crawl Status": rec.get('status')
            })

    if excel_rows:
        df = pd.DataFrame(excel_rows)

        df['Sort_Score'] = df['USM Requirement'].map(
            {'✅ PASS': 0, '⚠️ Q3/Q4': 1, '❌ Not Indexed': 2}).fillna(3)
        df['Q_Score'] = df['Best Quartile'].map(quartile_map).fillna(99)

        df = df.sort_values(by=['Sort_Score', 'Q_Score'])
        df = df.drop(columns=['Sort_Score', 'Q_Score'])

        df.to_excel(output_excel, index=False)
        logger.success(f"🎉 Report Generated: {output_excel}")
        print(f"👉 File saved at: {output_excel}")
    else:
        logger.warning("No valid data to export.")

# ==========================================
#              MAIN ENTRY
# ==========================================


if __name__ == '__main__':
    print("\n" + "="*60)
    print("   JCR AUTO TOOL - Developed by Ethan")
    print("   For: Gobithaasan Rudrusamy Research Group (USM)")
    print()
    print("⚠️  CHECK: Are you connected to USM Campus WiFi?")
    print("   (Access to JCR requires institutional network)")
    print("="*60 + "\n")

    # 1. Spider
    run_spider()

    # 2. Analysis
    run_analysis()

    print("\n✅ All jobs done! Script has finished successfully.")
