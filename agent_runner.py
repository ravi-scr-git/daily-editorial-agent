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
def generate_html_dashboard(conn: sqlite3.Connection, output_path: str = HTML_PATH):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM editorials ORDER BY date DESC, id DESC;")
    rows = cursor.fetchall()

    records = []
    for r in rows:
        records.append({
            "id": r["id"],
            "date": r["date"],
            "source": r["source"],
            "original_title": r["original_title"],
            "english_title": r["english_title"],
            "url": r["url"],
            "theme": r["theme"],
            "summary": r["summary"],
            "key_bullet_points": json.loads(r["key_bullet_points"]),
            "scope": r["scope"],
            "impact": r["impact"],
            "other_characteristics": json.loads(r["other_characteristics"])
        })

    records_json = json.dumps(records, ensure_ascii=False)
    available_dates = sorted(list(set(r["date"] for r in records)), reverse=True)
    dates_json = json.dumps(available_dates)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Editorial Intelligence | UPSC & Policy Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,700;0,900;1,400&family=Noto+Sans+Telugu:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Roboto', 'sans-serif'],
                        roboto: ['Roboto', 'sans-serif'],
                        telugu: ['Noto Sans Telugu', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            font-family: 'Roboto', sans-serif;
        }}
    </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <span class="bg-indigo-600 text-white font-black text-sm px-2.5 py-1 rounded">INSIGHT</span>
                    <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900">National Editorial Intelligence</h1>
                </div>
                <p class="text-xs sm:text-sm text-slate-500 mt-1">Autonomous daily synthesis of Eenadu, The Hindu, Indian Express & PIB powered by Gemini 2.5 Flash</p>
            </div>
            
            <!-- Quick Search Bar -->
            <div class="w-full md:w-80">
                <input type="text" id="searchInput" placeholder="Search keywords, acts, themes..." 
                       class="w-full text-sm bg-slate-100 border border-slate-300 rounded-lg px-3.5 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
        </div>
        
        <!-- Controls: Day Navigation & Source Tabs -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-3 pt-1 flex flex-wrap items-center justify-between gap-3 text-sm border-t border-slate-100">
            <!-- Day-Wise Selector -->
            <div class="flex items-center gap-2">
                <span class="font-semibold text-xs text-slate-400 uppercase tracking-wider">Date:</span>
                <select id="dateSelect" class="bg-slate-100 border border-slate-300 font-semibold text-slate-800 text-xs sm:text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"></select>
            </div>

            <!-- Source Tabs -->
            <div class="flex flex-wrap gap-1.5" id="sourceTabs">
                <button onclick="setSource('All')" data-source="All" class="source-btn px-3 py-1 rounded-full text-xs font-bold transition bg-indigo-600 text-white shadow-sm">All Sources</button>
                <button onclick="setSource('Eenadu')" data-source="Eenadu" class="source-btn px-3 py-1 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-200">ఈనాడు (Eenadu)</button>
                <button onclick="setSource('The Hindu')" data-source="The Hindu" class="source-btn px-3 py-1 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-200">The Hindu</button>
                <button onclick="setSource('Indian Express')" data-source="Indian Express" class="source-btn px-3 py-1 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-200">Indian Express</button>
                <button onclick="setSource('PIB')" data-source="PIB" class="source-btn px-3 py-1 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-200">PIB Releases</button>
            </div>
        </div>
    </header>

    <!-- Theme Pills Bar -->
    <div class="bg-slate-100/70 border-b border-slate-200 py-2.5">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-2 overflow-x-auto text-xs no-scrollbar" id="themePills">
            <span class="font-bold text-slate-400 uppercase tracking-wider text-[11px] shrink-0">Themes:</span>
            <!-- Dynamic themes injected by JS -->
        </div>
    </div>

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div id="statsBar" class="text-xs text-slate-500 font-medium mb-6"></div>
        <div id="articlesGrid" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
        <div id="emptyState" class="hidden text-center py-16 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <p class="text-slate-400 text-sm">No editorials matched the selected date, source, or search filters.</p>
        </div>
    </main>

    <footer class="mt-20 border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-400">
        Autonomous GitHub Actions Pipeline running Gemini 2.5 Flash. Hosted on GitHub Pages.
    </footer>

    <!-- Client-side interactive script -->
    <script>
        const articles = {records_json};
        const dates = {dates_json};

        let selectedDate = dates.length > 0 ? dates[0] : "";
        let selectedSource = "All";
        let selectedTheme = "All";
        let searchQuery = "";

        const sourceColor = {{
            "Eenadu": "bg-rose-50 text-rose-700 border-rose-200",
            "The Hindu": "bg-blue-50 text-blue-700 border-blue-200",
            "Indian Express": "bg-amber-50 text-amber-700 border-amber-200",
            "PIB": "bg-emerald-50 text-emerald-700 border-emerald-200"
        }};

        function init() {{
            const dateSelect = document.getElementById("dateSelect");
            dates.forEach(d => {{
                const opt = document.createElement("option");
                opt.value = d;
                opt.textContent = d;
                dateSelect.appendChild(opt);
            }});
            dateSelect.addEventListener("change", (e) => {{
                selectedDate = e.target.value;
                buildThemePills();
                render();
            }});

            document.getElementById("searchInput").addEventListener("input", (e) => {{
                searchQuery = e.target.value.toLowerCase().trim();
                render();
            }});

            buildThemePills();
            render();
        }}

        function setSource(src) {{
            selectedSource = src;
            document.querySelectorAll(".source-btn").forEach(btn => {{
                if (btn.dataset.source === src) {{
                    btn.className = "source-btn px-3 py-1 rounded-full text-xs font-bold transition bg-indigo-600 text-white shadow-sm";
                }} else {{
                    btn.className = "source-btn px-3 py-1 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-200";
                }}
            }});
            render();
        }}

        function buildThemePills() {{
            const container = document.getElementById("themePills");
            while (container.children.length > 1) container.removeChild(container.lastChild);

            const themes = new Set();
            articles.filter(a => !selectedDate || a.date === selectedDate).forEach(a => themes.add(a.theme));

            const allBtn = document.createElement("button");
            allBtn.textContent = "All Themes";
            allBtn.className = "theme-btn px-2.5 py-1 rounded-md font-semibold transition shrink-0 " + (selectedTheme === "All" ? "bg-slate-800 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100");
            allBtn.onclick = () => {{ selectedTheme = "All"; buildThemePills(); render(); }};
            container.appendChild(allBtn);

            themes.forEach(th => {{
                const btn = document.createElement("button");
                btn.textContent = th;
                btn.className = "theme-btn px-2.5 py-1 rounded-md font-medium transition shrink-0 " + (selectedTheme === th ? "bg-slate-800 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100");
                btn.onclick = () => {{ selectedTheme = th; buildThemePills(); render(); }};
                container.appendChild(btn);
            }});
        }}

        function render() {{
            const filtered = articles.filter(item => {{
                if (selectedDate && item.date !== selectedDate) return false;
                if (selectedSource !== "All" && item.source !== selectedSource) return false;
                if (selectedTheme !== "All" && item.theme !== selectedTheme) return false;
                if (searchQuery) {{
                    const fullHaystack = `${{item.original_title}} ${{item.english_title}} ${{item.summary}} ${{item.key_bullet_points.join(' ')}} ${{item.theme}} ${{JSON.stringify(item.other_characteristics)}}`.toLowerCase();
                    if (!fullHaystack.includes(searchQuery)) return false;
                }}
                return true;
            }});

            const grid = document.getElementById("articlesGrid");
            const empty = document.getElementById("emptyState");
            const stats = document.getElementById("statsBar");

            stats.textContent = `Showing ${{filtered.length}} editorial synthesis items for ${{selectedDate || 'all dates'}} (${{selectedSource}} | ${{selectedTheme}})`;

            if (filtered.length === 0) {{
                grid.innerHTML = "";
                empty.classList.remove("hidden");
                return;
            }}

            empty.classList.add("hidden");
            grid.innerHTML = filtered.map(item => {{
                const srcBadge = sourceColor[item.source] || "bg-slate-100 text-slate-700 border-slate-200";
                const bullets = item.key_bullet_points.map(b => `<li class="flex items-start gap-2 text-xs text-slate-700"><span class="text-indigo-500 font-bold shrink-0">•</span><span>${{b}}</span></li>`).join("");
                const acts = (item.other_characteristics.constitutional_articles_acts || []).map(a => `<span class="bg-indigo-50 text-indigo-700 font-semibold px-2 py-0.5 rounded text-[11px]">${{a}}</span>`).join(" ");

                return `
                <article class="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <span class="text-xs font-bold px-2.5 py-1 rounded-full border ${{srcBadge}}">${{item.source}}</span>
                            <div class="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                                <span class="bg-slate-100 px-2 py-0.5 rounded">${{item.theme}}</span>
                                <span class="bg-slate-100 px-2 py-0.5 rounded font-semibold text-slate-600">${{item.scope || 'National'}}</span>
                            </div>
                        </div>

                        <h2 class="font-serif font-bold text-lg text-slate-900 leading-snug hover:text-indigo-600 transition">
                            <a href="${{item.url}}" target="_blank" rel="noopener noreferrer">${{item.english_title}}</a>
                        </h2>
                        ${{item.source === 'Eenadu' ? `<p class="text-xs text-slate-500 font-medium mt-1 italic">${{item.original_title}}</p>` : ''}}

                        <p class="text-xs sm:text-sm text-slate-600 mt-3 font-serif leading-relaxed">${{item.summary}}</p>

                        <div class="mt-4 pt-4 border-t border-slate-100">
                            <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Key Insights</h3>
                            <ul class="space-y-1.5">${{bullets}}</ul>
                        </div>

                        ${{acts ? `
                        <div class="mt-4 pt-3 border-t border-slate-100">
                            <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Acts / Constitutional Articles</h3>
                            <div class="flex flex-wrap gap-1.5">${{acts}}</div>
                        </div>` : ''}}
                    </div>

                    <div class="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span class="text-slate-400">Tone: <strong class="text-slate-700">${{item.other_characteristics.tone || 'Analytical'}}</strong></span>
                        <a href="${{item.url}}" target="_blank" rel="noopener noreferrer" class="font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">Read Original Source &rarr;</a>
                    </div>
                </article>
                `;
            }}).join("");
        }}

        window.onload = init;
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n[Dashboard Generated] Successfully compiled {output_path} with {len(records)} records.")

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
