#!/usr/bin/env python3
"""
agent_runner.py - Autonomous Cloud-Ready Editorial Aggregator & Analysis Pipeline.
Scrapes editorials from Eenadu, The Hindu, Indian Express, and PIB.
Enriches with Gemini 2.5 Flash structured analysis, stores in SQLite, and generates index.html.
"""

import os
import sys
import json
import sqlite3
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Google GenAI SDK
from google import genai
from google.genai import types

# Playwright sync API
from playwright.sync_api import sync_playwright, Browser, Page

# =====================================================================
# Configuration & Database
# =====================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editorials.db")
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

def get_current_ist_date() -> str:
    """Returns today's date in IST (UTC+5:30)."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    return ist_now.strftime("%Y-%m-%d")

# =====================================================================
# Pydantic Schema for Gemini Structured Outputs
# =====================================================================
class OtherCharacteristics(BaseModel):
    tone: str = Field(description="Tone of the editorial: Critical, Constructive, Analytical, Advisory, or Informative")
    constitutional_articles_acts: List[str] = Field(
        default_factory=list,
        description="Constitutional Articles, legal Acts, Supreme Court verdicts, or official policies cited"
    )
    data_cited: List[str] = Field(
        default_factory=list,
        description="Key statistics, percentages, fiscal amounts, or economic indices mentioned"
    )

class EditorialAnalysis(BaseModel):
    date: str = Field(description="Publication date in YYYY-MM-DD format (IST)")
    source: str = Field(description="Publisher: Eenadu, The Hindu, Indian Express, or PIB")
    original_title: str = Field(description="Original editorial headline")
    english_title: str = Field(description="English translation of headline if in Telugu, otherwise identical headline")
    url: str = Field(description="Direct URL to article")
    theme: str = Field(description="Core theme: Governance & Polity, Economy, International Relations, Environment, Science & Tech, or Social Issues")
    summary: str = Field(description="Analytical, 3-4 sentence comprehensive summary")
    key_bullet_points: List[str] = Field(description="3 to 5 core arguments, insights, or takeaways")
    scope: str = Field(description="Scope: Regional, National, or International")
    impact: str = Field(description="Public policy implications, institutional consequence, or societal impact")
    other_characteristics: OtherCharacteristics

# =====================================================================
# Database Setup & Deduplication
# =====================================================================
def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS editorials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            original_title TEXT NOT NULL,
            english_title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            theme TEXT NOT NULL,
            summary TEXT NOT NULL,
            key_bullet_points TEXT NOT NULL,
            scope TEXT,
            impact TEXT,
            other_characteristics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ed_url ON editorials(url);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ed_date ON editorials(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ed_source ON editorials(source);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ed_theme ON editorials(theme);")
    conn.commit()
    return conn

def is_url_in_db(url: str, conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM editorials WHERE url = ? LIMIT 1;", (url,))
    return cursor.fetchone() is not None

def save_analysis(analysis: EditorialAnalysis, conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO editorials 
        (date, source, original_title, english_title, url, theme, summary, key_bullet_points, scope, impact, other_characteristics)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        analysis.date,
        analysis.source,
        analysis.original_title,
        analysis.english_title,
        analysis.url,
        analysis.theme,
        analysis.summary,
        json.dumps(analysis.key_bullet_points, ensure_ascii=False),
        analysis.scope,
        analysis.impact,
        json.dumps(analysis.other_characteristics.model_dump(), ensure_ascii=False)
    ))
    conn.commit()

# =====================================================================
# Gemini Structured Analysis
# =====================================================================
def analyze_article_with_gemini(raw_text: str, source: str, url: str, original_title: str) -> Optional[EditorialAnalysis]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  [Warning] GEMINI_API_KEY environment variable not found. Skipping AI analysis.")
        return None

    client = genai.Client(api_key=api_key)
    ist_date = get_current_ist_date()

    prompt = f"""
    You are an expert editorial analyst for Indian civil services and public policy research.
    Analyze the following editorial text published by '{source}' on {ist_date}.

    Source: {source}
    Article URL: {url}
    Original Title: {original_title}
    Text:
    {raw_text[:6000]}

    Provide the output strictly compliant with the requested JSON schema.
    If the article is in Telugu (Eenadu), accurately translate the title to English in 'english_title', and write all analysis fields in clean English.
    Ensure 'date' is '{ist_date}'.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EditorialAnalysis,
                temperature=0.2,
            ),
        )
        data = json.loads(response.text)
        return EditorialAnalysis(**data)
    except Exception as e:
        print(f"  [Error] Gemini analysis failed for {url}: {e}")
        return None

# =====================================================================
# Scrapers for the 4 Portals (Playwright)
# =====================================================================
def scrape_eenadu(browser: Browser, conn: sqlite3.Connection) -> List[EditorialAnalysis]:
    print("\n[1/4] Scraping Eenadu (Telugu Editorial)...")
    results = []
    page = browser.new_page()
    try:
        page.goto("https://www.eenadu.net/editorial", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        articles = page.locator("a[href*='/editorial/']").all()
        visited = set()
        for a in articles[:4]:
            href = a.get_attribute("href")
            title = a.inner_text().strip()
            if not href or not title or href in visited:
                continue
            if not href.startswith("http"):
                href = f"https://www.eenadu.net{href}"
            visited.add(href)

            if is_url_in_db(href, conn):
                print(f"  [Skipped - Exists] {title[:40]}...")
                continue

            art_page = browser.new_page()
            try:
                art_page.goto(href, timeout=30000, wait_until="domcontentloaded")
                body_text = art_page.locator("div.fullstory, div.story-details, article").inner_text()
                if body_text:
                    print(f"  Analyzing Eenadu: {title[:45]}...")
                    analysis = analyze_article_with_gemini(body_text, "Eenadu", href, title)
                    if analysis:
                        save_analysis(analysis, conn)
                        results.append(analysis)
            except Exception as ex:
                print(f"  Failed to load Eenadu article: {ex}")
            finally:
                art_page.close()
    except Exception as e:
        print(f"  Eenadu scraper error: {e}")
    finally:
        page.close()
    return results

def scrape_the_hindu(browser: Browser, conn: sqlite3.Connection) -> List[EditorialAnalysis]:
    print("\n[2/4] Scraping The Hindu (Editorials)...")
    results = []
    page = browser.new_page()
    try:
        page.goto("https://www.thehindu.com/opinion/editorial/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        links = page.locator("h3.title a, div.story-card a[href*='/opinion/editorial/']").all()
        visited = set()
        for a in links[:4]:
            href = a.get_attribute("href")
            title = a.inner_text().strip()
            if not href or not title or href in visited:
                continue
            if not href.startswith("http"):
                href = f"https://www.thehindu.com{href}"
            visited.add(href)

            if is_url_in_db(href, conn):
                print(f"  [Skipped - Exists] {title[:40]}...")
                continue

            art_page = browser.new_page()
            try:
                art_page.goto(href, timeout=30000, wait_until="domcontentloaded")
                paragraphs = art_page.locator("div.articlebodycontent p, div[itemprop='articleBody'] p").all_inner_texts()
                body_text = "\n\n".join(paragraphs)
                if body_text:
                    print(f"  Analyzing The Hindu: {title[:45]}...")
                    analysis = analyze_article_with_gemini(body_text, "The Hindu", href, title)
                    if analysis:
                        save_analysis(analysis, conn)
                        results.append(analysis)
            except Exception as ex:
                print(f"  Failed to load The Hindu article: {ex}")
            finally:
                art_page.close()
    except Exception as e:
        print(f"  The Hindu scraper error: {e}")
    finally:
        page.close()
    return results

def scrape_indian_express(browser: Browser, conn: sqlite3.Connection) -> List[EditorialAnalysis]:
    print("\n[3/4] Scraping Indian Express (Editorials)...")
    results = []
    page = browser.new_page()
    try:
        page.goto("https://indianexpress.com/section/opinion/editorials/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        links = page.locator("div.articles h2.title a, div.article-list a[href*='/article/opinion/editorials/']").all()
        visited = set()
        for a in links[:4]:
            href = a.get_attribute("href")
            title = a.inner_text().strip()
            if not href or not title or href in visited:
                continue
            visited.add(href)

            if is_url_in_db(href, conn):
                print(f"  [Skipped - Exists] {title[:40]}...")
                continue

            art_page = browser.new_page()
            try:
                art_page.goto(href, timeout=30000, wait_until="domcontentloaded")
                paragraphs = art_page.locator("div.story-details p, div#pcl-full-content p").all_inner_texts()
                body_text = "\n\n".join(paragraphs)
                if body_text:
                    print(f"  Analyzing Indian Express: {title[:45]}...")
                    analysis = analyze_article_with_gemini(body_text, "Indian Express", href, title)
                    if analysis:
                        save_analysis(analysis, conn)
                        results.append(analysis)
            except Exception as ex:
                print(f"  Failed to load Express article: {ex}")
            finally:
                art_page.close()
    except Exception as e:
        print(f"  Indian Express scraper error: {e}")
    finally:
        page.close()
    return results

def scrape_pib(browser: Browser, conn: sqlite3.Connection) -> List[EditorialAnalysis]:
    print("\n[4/4] Scraping PIB (National Releases & Features)...")
    results = []
    page = browser.new_page()
    try:
        page.goto("https://pib.gov.in/AllRelease.aspx", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        links = page.locator("ul.num li a[href*='PRID=']").all()
        visited = set()
        for a in links[:4]:
            href = a.get_attribute("href")
            title = a.inner_text().strip()
            if not href or not title or href in visited:
                continue
            if not href.startswith("http"):
                href = f"https://pib.gov.in/{href}"
            visited.add(href)

            if is_url_in_db(href, conn):
                print(f"  [Skipped - Exists] {title[:40]}...")
                continue

            art_page = browser.new_page()
            try:
                art_page.goto(href, timeout=30000, wait_until="domcontentloaded")
                body_text = art_page.locator("div.innner-page-main-about-us").inner_text()
                if body_text:
                    print(f"  Analyzing PIB Release: {title[:45]}...")
                    analysis = analyze_article_with_gemini(body_text, "PIB", href, title)
                    if analysis:
                        save_analysis(analysis, conn)
                        results.append(analysis)
            except Exception as ex:
                print(f"  Failed to load PIB article: {ex}")
            finally:
                art_page.close()
    except Exception as e:
        print(f"  PIB scraper error: {e}")
    finally:
        page.close()
    return results

# =====================================================================
# GitHub Pages HTML Dashboard Compiler
# =====================================================================
from generate_site import generate_static_site

def generate_html_dashboard(conn: sqlite3.Connection = None, output_path: str = HTML_PATH):
    print(f"\n[Compiling Dashboard] Generating eye-safe, strain-free index.html...")
    return generate_static_site(output_path=output_path, db_path=DB_PATH)

# =====================================================================
# Main Execution Pipeline
# =====================================================================
def main():
    print("==================================================================")
    print(f" DAILY EDITORIAL SCRAPER & GEMINI PIPELINE: {get_current_ist_date()} IST")
    print("==================================================================")
    conn = init_db()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            scrape_eenadu(browser, conn)
            scrape_the_hindu(browser, conn)
            scrape_indian_express(browser, conn)
            scrape_pib(browser, conn)
        finally:
            browser.close()

    generate_html_dashboard(conn)
    conn.close()
    print("==================================================================")
    print(" PIPELINE COMPLETED SUCCESSFULLY")
    print("==================================================================")

if __name__ == "__main__":
    main()
