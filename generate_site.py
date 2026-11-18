#!/usr/bin/env python3
"""
generate_site.py
Generates an eye-safe, strain-free, mobile-optimized standalone static dashboard (index.html)
from SQLite database (editorials.db).
Mobile-Friendly:
- Bulky sidebar hidden on mobile, replaced by compact mobile dropdowns.
- Large non-link stat cards hidden on mobile, replaced by a 1-line compact ticker.
- Desktop keeps the full sidebar, normal stat cards, pills, and archive lists.
- Eye-Care Warm Paper (Sepia), Daylight, and Night modes with font zoom.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

from db_manager import get_all_editorials, get_available_dates, DEFAULT_DB_PATH

OUTPUT_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

def parse_field(field_val: Any, default: Any = None) -> Any:
    """Helper to parse JSON fields safely."""
    if not field_val:
        return default if default is not None else {}
    if isinstance(field_val, (dict, list)):
        return field_val
    try:
        return json.loads(field_val)
    except Exception:
        return field_val

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Editorial Intelligence | Eye-Safe Policy Reader</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts: Roboto & Noto Sans Telugu -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,700;0,900;1,400&family=Noto+Sans+Telugu:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        /* Eye-Safe Reading Theme Palettes */
        :root, body.theme-warm {
            --bg-main: #FAF6EF;          /* Gentle Natural Ivory Paper */
            --bg-header: #FFFDF9;
            --bg-card: #FFFDF9;
            --bg-subtle: #F3ECE0;
            --bg-highlight: #EDE3D4;
            --border-card: #E4D9C5;
            --border-subtle: #EBE1D0;
            --text-primary: #24292F;      /* Soft deep charcoal - zero harsh glare */
            --text-secondary: #4A5568;    /* High contrast secondary */
            --text-muted: #64748B;
            --accent-primary: #4338CA;
            --accent-bg: #EEF2FF;
            --accent-border: #C7D2FE;
            --card-shadow: 0 2px 5px rgba(60, 45, 20, 0.05);
        }

        body.theme-day {
            --bg-main: #F8FAFC;          /* Crisp Daylight */
            --bg-header: #FFFFFF;
            --bg-card: #FFFFFF;
            --bg-subtle: #F1F5F9;
            --bg-highlight: #E2E8F0;
            --border-card: #CBD5E1;
            --border-subtle: #E2E8F0;
            --text-primary: #0F172A;      /* Deepest slate */
            --text-secondary: #334155;
            --text-muted: #64748B;
            --accent-primary: #3730A3;
            --accent-bg: #EEF2FF;
            --accent-border: #C7D2FE;
            --card-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
        }

        body.theme-dark {
            --bg-main: #0F172A;          /* Deep Twilight Slate - Zero Blue Light */
            --bg-header: #1E293B;
            --bg-card: #1E293B;
            --bg-subtle: #162032;
            --bg-highlight: #283548;
            --border-card: #334155;
            --border-subtle: #283548;
            --text-primary: #F1F5F9;      /* Crisp soft reading white */
            --text-secondary: #CBD5E1;    /* High readability silver */
            --text-muted: #94A3B8;
            --accent-primary: #818CF8;
            --accent-bg: #232D48;
            --accent-border: #3B4B75;
            --card-shadow: 0 4px 10px rgba(0, 0, 0, 0.35);
        }

        /* Typography & Core Styles */
        body {
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.7;
            letter-spacing: 0.012em;
            transition: background-color 0.25s ease, color 0.25s ease;
        }

        .telugu-text {
            font-family: 'Noto Sans Telugu', 'Roboto', sans-serif;
            line-height: 1.85;
        }

        .card-surface {
            background-color: var(--bg-card);
            border-color: var(--border-card);
            box-shadow: var(--card-shadow);
        }

        .subtle-surface {
            background-color: var(--bg-subtle);
            border-color: var(--border-subtle);
        }

        /* Font Scaling Modes */
        body.font-scale-sm {
            --fs-body: 0.9375rem;    /* 15px */
            --fs-reading: 1.0rem;    /* 16px */
            --fs-headline: 1.25rem;  /* 20px */
        }
        body.font-scale-md {
            --fs-body: 1.0rem;       /* 16px */
            --fs-reading: 1.09375rem;/* 17.5px */
            --fs-headline: 1.375rem; /* 22px */
        }
        body.font-scale-lg {
            --fs-body: 1.09375rem;   /* 17.5px */
            --fs-reading: 1.21875rem;/* 19.5px */
            --fs-headline: 1.5625rem;/* 25px */
        }

        .reading-summary {
            font-size: var(--fs-reading);
            line-height: 1.78;
        }

        .reading-bullet {
            font-size: var(--fs-body);
            line-height: 1.72;
        }

        .card-headline {
            font-size: var(--fs-headline);
            line-height: 1.35;
        }

        /* Hide horizontal scrollbar but preserve scrollability */
        .no-scrollbar::-webkit-scrollbar {
            display: none;
        }
        .no-scrollbar {
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
    </style>
</head>
<body class="theme-warm font-scale-md antialiased min-h-screen flex flex-col">

    <!-- Top Sticky Header -->
    <header class="sticky top-0 z-40 border-b backdrop-blur-md transition duration-200" style="background-color: var(--bg-header); border-color: var(--border-card);">
        <div class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16 sm:h-20">
                
                <!-- Logo & Branding -->
                <div class="flex items-center space-x-2.5 sm:space-x-3.5">
                    <div class="w-9 h-9 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-tr from-indigo-700 via-indigo-600 to-blue-600 flex items-center justify-center text-white shadow-md flex-shrink-0">
                        <i class="fa-solid fa-book-open-reader text-lg sm:text-xl"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h1 class="text-base sm:text-2xl font-black tracking-tight" style="color: var(--text-primary);">Editorial Intellect</h1>
                            <span class="hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border" style="background-color: var(--bg-subtle); color: var(--accent-primary); border-color: var(--border-card);">
                                <i class="fa-solid fa-shield-halved mr-1 text-[11px]"></i> Eye-Safe
                            </span>
                        </div>
                        <p class="text-[11px] sm:text-xs font-medium line-clamp-1" style="color: var(--text-muted);">
                            Daily Multi-Source Editorial Synthesis
                        </p>
                    </div>
                </div>

                <!-- Eye Comfort Controls (Theme & Font Size) -->
                <div class="flex items-center space-x-1.5 sm:space-x-3">
                    
                    <!-- Font Zoom Controls -->
                    <div class="flex items-center rounded-xl p-0.5 sm:p-1 border" style="background-color: var(--bg-subtle); border-color: var(--border-card);" title="Adjust Text Size">
                        <button onclick="setFontScale('sm')" id="fontBtn-sm" class="px-2 sm:px-2.5 py-1 text-xs font-bold rounded-lg transition">A-</button>
                        <button onclick="setFontScale('md')" id="fontBtn-md" class="px-2 sm:px-2.5 py-1 text-xs font-bold rounded-lg transition">A</button>
                        <button onclick="setFontScale('lg')" id="fontBtn-lg" class="px-2 sm:px-2.5 py-1 text-xs font-bold rounded-lg transition">A+</button>
                    </div>

                    <!-- Theme Switcher Pills -->
                    <div class="flex items-center rounded-xl p-0.5 sm:p-1 border" style="background-color: var(--bg-subtle); border-color: var(--border-card);">
                        <button onclick="setTheme('warm')" id="themeBtn-warm" class="px-2 sm:px-3 py-1 sm:py-1.5 text-xs font-bold rounded-lg flex items-center space-x-1 transition" title="Warm Paper (Kindle Sepia Mode)">
                            <i class="fa-solid fa-book text-amber-600"></i>
                            <span class="hidden md:inline">Warm</span>
                        </button>
                        <button onclick="setTheme('day')" id="themeBtn-day" class="px-2 sm:px-3 py-1 sm:py-1.5 text-xs font-bold rounded-lg flex items-center space-x-1 transition" title="Clean Daylight Mode">
                            <i class="fa-solid fa-sun text-amber-500"></i>
                            <span class="hidden md:inline">Day</span>
                        </button>
                        <button onclick="setTheme('dark')" id="themeBtn-dark" class="px-2 sm:px-3 py-1 sm:py-1.5 text-xs font-bold rounded-lg flex items-center space-x-1 transition" title="Night / Dark Mode">
                            <i class="fa-solid fa-moon text-indigo-400"></i>
                            <span class="hidden md:inline">Night</span>
                        </button>
                    </div>

                </div>

            </div>
        </div>
    </header>

    <!-- Main Container -->
    <div class="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8 w-full flex-1">
        
        <!-- Desktop Summary Stat Cards (Hidden on Mobile to Save Vertical Space) -->
        <div class="hidden lg:grid lg:grid-cols-4 gap-4 mb-8">
            <div class="card-surface p-5 rounded-2xl border flex items-center space-x-3.5">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl" style="background-color: var(--accent-bg); color: var(--accent-primary);">
                    <i class="fa-solid fa-newspaper"></i>
                </div>
                <div>
                    <div class="text-3xl font-extrabold tracking-tight" id="statTotalArticles">0</div>
                    <div class="text-sm font-semibold" style="color: var(--text-muted);">Editorials Synthesized</div>
                </div>
            </div>

            <div class="card-surface p-5 rounded-2xl border flex items-center space-x-3.5">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl bg-rose-50 text-rose-700 border border-rose-200">
                    <i class="fa-solid fa-language"></i>
                </div>
                <div>
                    <div class="text-3xl font-extrabold tracking-tight text-rose-700" id="statEenaduCount">0</div>
                    <div class="text-sm font-semibold" style="color: var(--text-muted);">ఈనాడు (Eenadu Telugu)</div>
                </div>
            </div>

            <div class="card-surface p-5 rounded-2xl border flex items-center space-x-3.5">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl bg-blue-50 text-blue-700 border border-blue-200">
                    <i class="fa-solid fa-feather-pointed"></i>
                </div>
                <div>
                    <div class="text-3xl font-extrabold tracking-tight text-blue-700" id="statEnglishCount">0</div>
                    <div class="text-sm font-semibold" style="color: var(--text-muted);">Hindu, Express & PIB</div>
                </div>
            </div>

            <div class="card-surface p-5 rounded-2xl border flex items-center space-x-3.5">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <i class="fa-solid fa-layer-group"></i>
                </div>
                <div>
                    <div class="text-3xl font-extrabold tracking-tight text-emerald-700" id="statThemesCount">0</div>
                    <div class="text-sm font-semibold" style="color: var(--text-muted);">Governance Themes</div>
                </div>
            </div>
        </div>

        <!-- 2-Column Responsive Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">
            
            <!-- Left Sidebar Navigation (Desktop ONLY: hidden lg:block) -->
            <!-- Prevents the bulky sidebar from pushing articles off-screen on mobile -->
            <aside class="hidden lg:block lg:col-span-1 space-y-6">
                
                <!-- Day-Wise Date Navigator -->
                <div class="card-surface rounded-2xl border p-5">
                    <h2 class="text-xs font-bold uppercase tracking-wider mb-3.5 flex items-center justify-between" style="color: var(--text-muted);">
                        <span><i class="fa-regular fa-calendar-check mr-2" style="color: var(--accent-primary);"></i> Daily Archive</span>
                        <span class="text-xs font-semibold" id="dateArchiveCount"></span>
                    </h2>
                    
                    <div class="space-y-1.5" id="dateListContainer">
                        <!-- Populated by JS for Desktop -->
                    </div>
                </div>

                <!-- Theme Filter -->
                <div class="card-surface rounded-2xl border p-5">
                    <div class="flex items-center justify-between mb-3.5">
                        <h2 class="text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
                            <i class="fa-solid fa-tags mr-2" style="color: var(--accent-primary);"></i> Themes
                        </h2>
                        <button onclick="clearThemeFilter()" class="text-xs font-bold hover:underline" style="color: var(--accent-primary);">Reset</button>
                    </div>
                    
                    <div class="flex flex-wrap gap-2" id="themePillsContainer">
                        <!-- Populated by JS for Desktop -->
                    </div>
                </div>

                <!-- Scope Filter -->
                <div class="card-surface rounded-2xl border p-5">
                    <h2 class="text-xs font-bold uppercase tracking-wider mb-3.5" style="color: var(--text-muted);">
                        <i class="fa-solid fa-compass mr-2" style="color: var(--accent-primary);"></i> Scope
                    </h2>
                    <div class="flex flex-wrap gap-2" id="scopePillsContainer">
                        <!-- Populated by JS for Desktop -->
                    </div>
                </div>

                <!-- Reading Advice -->
                <div class="rounded-2xl p-5 border text-xs leading-relaxed" style="background-color: var(--bg-subtle); border-color: var(--border-card); color: var(--text-secondary);">
                    <div class="font-bold mb-1.5 flex items-center text-sm" style="color: var(--text-primary);">
                        <i class="fa-solid fa-eye text-emerald-600 mr-2"></i> Eye Comfort Advice
                    </div>
                    Switch to <strong>Warm Paper</strong> mode for extended reading sessions to reduce digital optical strain.
                </div>

            </aside>

            <!-- Main Content Area -->
            <main class="lg:col-span-3 space-y-4 sm:space-y-6">
                
                <!-- Mobile Compact Ticker Bar (Mobile Only: lg:hidden) -->
                <div class="block lg:hidden card-surface rounded-xl border px-3 py-2 flex items-center justify-between text-xs font-semibold">
                    <div class="flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        <span><strong id="statMobileTotal" class="font-bold text-sm">0</strong> Editorials</span>
                    </div>
                    <div class="flex items-center space-x-2.5 text-[11px]" style="color: var(--text-muted);">
                        <span class="text-rose-700 font-bold">ఈనాడు: <span id="statMobileEenadu">0</span></span>
                        <span>•</span>
                        <span class="text-blue-700 font-bold">English: <span id="statMobileEnglish">0</span></span>
                    </div>
                </div>

                <!-- Mobile Dropdown Controls (Mobile Only: lg:hidden) -->
                <!-- Replaces the bulky sidebar with sleek, compact dropdowns -->
                <div class="block lg:hidden card-surface rounded-xl border p-3.5 space-y-3" style="border-color: var(--border-card);">
                    <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider" style="color: var(--text-muted);">
                        <span><i class="fa-solid fa-sliders mr-1.5" style="color: var(--accent-primary);"></i> Filters (Dropdown)</span>
                        <button onclick="resetAllFilters()" class="text-xs font-bold hover:underline" style="color: var(--accent-primary);">Reset All</button>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                        <!-- Date Dropdown -->
                        <div>
                            <label class="block text-[11px] font-bold mb-1" style="color: var(--text-muted);">Date Archive:</label>
                            <select id="mobileDateSelect" onchange="selectDate(this.value)" class="w-full py-2 px-2.5 rounded-lg border font-semibold text-xs outline-none" style="background-color: var(--bg-subtle); color: var(--text-primary); border-color: var(--border-card);">
                            </select>
                        </div>

                        <!-- Theme Dropdown -->
                        <div>
                            <label class="block text-[11px] font-bold mb-1" style="color: var(--text-muted);">Theme Filter:</label>
                            <select id="mobileThemeSelect" onchange="selectTheme(this.value)" class="w-full py-2 px-2.5 rounded-lg border font-semibold text-xs outline-none" style="background-color: var(--bg-subtle); color: var(--text-primary); border-color: var(--border-card);">
                            </select>
                        </div>

                        <!-- Scope Dropdown -->
                        <div>
                            <label class="block text-[11px] font-bold mb-1" style="color: var(--text-muted);">Geographic Scope:</label>
                            <select id="mobileScopeSelect" onchange="selectScope(this.value)" class="w-full py-2 px-2.5 rounded-lg border font-semibold text-xs outline-none" style="background-color: var(--bg-subtle); color: var(--text-primary); border-color: var(--border-card);">
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Search & Source Tabs Bar -->
                <div class="card-surface rounded-2xl border p-4 sm:p-5 space-y-3.5 sm:space-y-4">
                    
                    <!-- Search Input -->
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3.5 sm:pl-4 flex items-center pointer-events-none text-sm sm:text-base" style="color: var(--text-muted);">
                            <i class="fa-solid fa-magnifying-glass"></i>
                        </div>
                        <input 
                            type="text" 
                            id="searchInput" 
                            oninput="onSearchChange()" 
                            placeholder="Search editorials, Supreme Court verdicts, acts..." 
                            class="w-full pl-10 sm:pl-11 pr-10 py-2.5 sm:py-3 rounded-xl border text-xs sm:text-base font-medium outline-none transition focus:ring-2 focus:ring-indigo-500"
                            style="background-color: var(--bg-main); color: var(--text-primary); border-color: var(--border-card);"
                        >
                        <button 
                            id="clearSearchBtn" 
                            onclick="clearSearch()" 
                            class="hidden absolute inset-y-0 right-0 pr-3.5 flex items-center hover:opacity-80 transition"
                            style="color: var(--text-muted);"
                        >
                            <i class="fa-solid fa-circle-xmark text-base"></i>
                        </button>
                    </div>

                    <!-- Source Selection Tabs -->
                    <div class="flex items-center justify-between border-t pt-3 flex-wrap gap-2.5" style="border-color: var(--border-subtle);">
                        <div class="flex flex-wrap gap-1.5 sm:gap-2" id="sourceTabsContainer">
                            <!-- Populated by JS -->
                        </div>

                        <div class="text-xs font-semibold flex items-center space-x-2" style="color: var(--text-muted);">
                            <span>Showing <strong class="font-extrabold text-xs sm:text-sm" style="color: var(--text-primary);" id="filteredCount">0</strong> articles</span>
                            <button onclick="resetAllFilters()" class="text-xs font-bold hover:underline ml-1 hidden sm:inline" style="color: var(--accent-primary);">
                                Clear All
                            </button>
                        </div>
                    </div>

                </div>

                <!-- Articles List Container -->
                <div id="articlesList" class="space-y-4 sm:space-y-6">
                    <!-- Populated by JS -->
                </div>

                <!-- Empty State -->
                <div id="emptyState" class="hidden card-surface rounded-2xl border p-8 sm:p-12 text-center space-y-3">
                    <div class="w-14 h-14 rounded-full mx-auto flex items-center justify-center text-xl" style="background-color: var(--bg-subtle); color: var(--text-muted);">
                        <i class="fa-solid fa-filter-circle-xmark"></i>
                    </div>
                    <h3 class="text-base sm:text-lg font-bold" style="color: var(--text-primary);">No Editorials Found</h3>
                    <p class="text-xs sm:text-sm max-w-md mx-auto" style="color: var(--text-muted);">No articles matched the selected date, source, theme, or search criteria.</p>
                    <button onclick="resetAllFilters()" class="px-4 py-2 rounded-xl font-bold text-xs sm:text-sm transition text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm">
                        Reset All Filters
                    </button>
                </div>

            </main>

        </div>

    </div>

    <!-- Footer -->
    <footer class="mt-12 sm:mt-16 border-t py-6 sm:py-8 text-center text-xs sm:text-sm font-medium transition duration-200" style="background-color: var(--bg-header); border-color: var(--border-card); color: var(--text-muted);">
        <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2.5">
            <div>
                <strong>Editorial Intellect</strong> — Autonomous Daily Multi-Source Policy Synthesizer
            </div>
            <div class="flex items-center space-x-3 text-xs">
                <span>Autonomous Cloud Pipeline</span>
                <span>•</span>
                <span>GitHub Pages</span>
            </div>
        </div>
    </footer>

    <!-- Client-Side Interactive Logic -->
    <script>
        const RAW_EDITORIALS = __EDITORIALS_JSON__;
        const AVAILABLE_DATES = __DATES_JSON__;

        const state = {
            selectedDate: AVAILABLE_DATES.length > 0 ? AVAILABLE_DATES[0] : 'ALL',
            selectedSource: 'ALL',
            selectedTheme: 'ALL',
            selectedScope: 'ALL',
            searchQuery: '',
            expandedCards: {},
            theme: localStorage.getItem('editorial_theme') || 'warm',
            fontScale: localStorage.getItem('editorial_font_scale') || 'md'
        };

        const SOURCE_CONFIG = {
            'Eenadu': {
                label: 'ఈనాడు (Eenadu)',
                icon: 'fa-language',
                badgeBg: 'bg-rose-50 text-rose-800 border-rose-300 font-bold',
                headerBorder: 'border-l-[4px] sm:border-l-[5px] border-rose-600',
                btnClass: 'hover:bg-rose-50 hover:text-rose-700'
            },
            'The Hindu': {
                label: 'The Hindu',
                icon: 'fa-landmark',
                badgeBg: 'bg-blue-50 text-blue-900 border-blue-300 font-bold',
                headerBorder: 'border-l-[4px] sm:border-l-[5px] border-slate-900',
                btnClass: 'hover:bg-blue-50 hover:text-blue-900'
            },
            'Indian Express': {
                label: 'Indian Express',
                icon: 'fa-feather',
                badgeBg: 'bg-amber-50 text-amber-900 border-amber-300 font-bold',
                headerBorder: 'border-l-[4px] sm:border-l-[5px] border-amber-600',
                btnClass: 'hover:bg-amber-50 hover:text-amber-800'
            },
            'PIB': {
                label: 'PIB Releases',
                icon: 'fa-bullhorn',
                badgeBg: 'bg-emerald-50 text-emerald-900 border-emerald-300 font-bold',
                headerBorder: 'border-l-[4px] sm:border-l-[5px] border-emerald-600',
                btnClass: 'hover:bg-emerald-50 hover:text-emerald-800'
            }
        };

        // Theme and Font Scale Controls
        function setTheme(mode) {
            state.theme = mode;
            localStorage.setItem('editorial_theme', mode);
            document.body.className = `theme-${mode} font-scale-${state.fontScale} antialiased min-h-screen flex flex-col`;
            
            ['warm', 'day', 'dark'].forEach(m => {
                const btn = document.getElementById(`themeBtn-${m}`);
                if (btn) {
                    if (m === mode) {
                        btn.style.backgroundColor = 'var(--bg-card)';
                        btn.style.boxShadow = 'var(--card-shadow)';
                        btn.style.color = 'var(--text-primary)';
                    } else {
                        btn.style.backgroundColor = 'transparent';
                        btn.style.boxShadow = 'none';
                        btn.style.color = 'var(--text-muted)';
                    }
                }
            });
        }

        function setFontScale(scale) {
            state.fontScale = scale;
            localStorage.setItem('editorial_font_scale', scale);
            document.body.className = `theme-${state.theme} font-scale-${scale} antialiased min-h-screen flex flex-col`;

            ['sm', 'md', 'lg'].forEach(s => {
                const btn = document.getElementById(`fontBtn-${s}`);
                if (btn) {
                    if (s === scale) {
                        btn.style.backgroundColor = 'var(--bg-card)';
                        btn.style.boxShadow = 'var(--card-shadow)';
                        btn.style.color = 'var(--text-primary)';
                    } else {
                        btn.style.backgroundColor = 'transparent';
                        btn.style.boxShadow = 'none';
                        btn.style.color = 'var(--text-muted)';
                    }
                }
            });
        }

        function updateStats() {
            const total = RAW_EDITORIALS.length;
            const eenaduCount = RAW_EDITORIALS.filter(e => e.source === 'Eenadu').length;
            const englishCount = RAW_EDITORIALS.filter(e => e.source !== 'Eenadu').length;
            const themes = new Set(RAW_EDITORIALS.map(e => e.theme).filter(Boolean));

            // Desktop stats
            const totalEl = document.getElementById('statTotalArticles');
            if (totalEl) totalEl.innerText = total;
            const eenaduEl = document.getElementById('statEenaduCount');
            if (eenaduEl) eenaduEl.innerText = eenaduCount;
            const engEl = document.getElementById('statEnglishCount');
            if (engEl) engEl.innerText = englishCount;
            const themesEl = document.getElementById('statThemesCount');
            if (themesEl) themesEl.innerText = themes.size;

            // Mobile ticker stats
            const mobTotal = document.getElementById('statMobileTotal');
            if (mobTotal) mobTotal.innerText = total;
            const mobEenadu = document.getElementById('statMobileEenadu');
            if (mobEenadu) mobEenadu.innerText = eenaduCount;
            const mobEnglish = document.getElementById('statMobileEnglish');
            if (mobEnglish) mobEnglish.innerText = englishCount;
        }

        // Populate Mobile Dropdowns (Theme, Date, Scope)
        function renderMobileDropdowns() {
            // Date dropdown
            const dateSel = document.getElementById('mobileDateSelect');
            if (dateSel) {
                let dOpts = `<option value="ALL">All Available Dates (${RAW_EDITORIALS.length})</option>`;
                AVAILABLE_DATES.forEach(dt => {
                    const cnt = RAW_EDITORIALS.filter(e => e.date === dt).length;
                    dOpts += `<option value="${dt}">${dt} (${cnt} articles)</option>`;
                });
                dateSel.innerHTML = dOpts;
                dateSel.value = state.selectedDate;
            }

            // Theme dropdown
            const themeSel = document.getElementById('mobileThemeSelect');
            if (themeSel) {
                const allThemes = Array.from(new Set(RAW_EDITORIALS.map(e => e.theme).filter(Boolean))).sort();
                let tOpts = `<option value="ALL">All Themes (${allThemes.length})</option>`;
                allThemes.forEach(th => {
                    tOpts += `<option value="${th}">${th}</option>`;
                });
                themeSel.innerHTML = tOpts;
                themeSel.value = state.selectedTheme;
            }

            // Scope dropdown
            const scopeSel = document.getElementById('mobileScopeSelect');
            if (scopeSel) {
                const allScopes = Array.from(new Set(RAW_EDITORIALS.map(e => e.scope).filter(Boolean))).sort();
                let sOpts = `<option value="ALL">All Scopes</option>`;
                allScopes.forEach(sc => {
                    sOpts += `<option value="${sc}">${sc}</option>`;
                });
                scopeSel.innerHTML = sOpts;
                scopeSel.value = state.selectedScope;
            }
        }

        function renderDateList() {
            const container = document.getElementById('dateListContainer');
            if (!container) return;
            const archiveEl = document.getElementById('dateArchiveCount');
            if (archiveEl) archiveEl.innerText = `${AVAILABLE_DATES.length} Days`;

            let html = `
                <button onclick="selectDate('ALL')" class="w-full text-left px-3.5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center justify-between ${
                    state.selectedDate === 'ALL'
                        ? 'text-white bg-indigo-600 shadow-sm'
                        : 'hover:opacity-80'
                }" style="${state.selectedDate === 'ALL' ? '' : 'color: var(--text-secondary); background-color: var(--bg-subtle);'}">
                    <span><i class="fa-solid fa-calendar-week mr-2"></i> All Available Dates</span>
                    <span class="text-xs px-2 py-0.5 rounded-full ${state.selectedDate === 'ALL' ? 'bg-indigo-800 text-white' : 'border'}" style="${state.selectedDate === 'ALL' ? '' : 'border-color: var(--border-card);'}">${RAW_EDITORIALS.length}</span>
                </button>
            `;

            AVAILABLE_DATES.forEach(dt => {
                const count = RAW_EDITORIALS.filter(e => e.date === dt).length;
                const isSelected = state.selectedDate === dt;
                html += `
                    <button onclick="selectDate('${dt}')" class="w-full text-left px-3.5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center justify-between ${
                        isSelected
                            ? 'text-white bg-indigo-600 shadow-sm'
                            : 'hover:opacity-80'
                    }" style="${isSelected ? '' : 'color: var(--text-secondary); background-color: var(--bg-subtle);'}">
                        <span><i class="fa-regular fa-calendar mr-2"></i> ${dt}</span>
                        <span class="text-xs px-2 py-0.5 rounded-full ${isSelected ? 'bg-indigo-800 text-white' : 'border'}" style="${isSelected ? '' : 'border-color: var(--border-card);'}">${count}</span>
                    </button>
                `;
            });

            container.innerHTML = html;
        }

        function renderSourceTabs() {
            const container = document.getElementById('sourceTabsContainer');
            if (!container) return;
            const sources = ['ALL', 'Eenadu', 'The Hindu', 'Indian Express', 'PIB'];

            let html = '';
            sources.forEach(src => {
                const isSelected = state.selectedSource === src;
                let label = src === 'ALL' ? 'All Sources' : (SOURCE_CONFIG[src]?.label || src);
                let count = RAW_EDITORIALS.filter(e => {
                    const matchDate = state.selectedDate === 'ALL' || e.date === state.selectedDate;
                    const matchSrc = src === 'ALL' || e.source === src;
                    return matchDate && matchSrc;
                }).length;

                html += `
                    <button onclick="selectSource('${src}')" class="px-2.5 sm:px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold transition flex items-center space-x-1 sm:space-x-1.5 ${
                        isSelected
                            ? 'text-white bg-indigo-600 shadow-sm'
                            : 'border hover:opacity-85'
                    }" style="${isSelected ? '' : 'background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);'}">
                        <span>${label}</span>
                        <span class="text-[10px] sm:text-xs px-1.5 py-0.2 rounded-full ${isSelected ? 'bg-indigo-800 text-white' : 'border'}" style="${isSelected ? '' : 'border-color: var(--border-card);'}">${count}</span>
                    </button>
                `;
            });

            container.innerHTML = html;
        }

        function renderThemePills() {
            const container = document.getElementById('themePillsContainer');
            if (!container) return;
            const allThemes = Array.from(new Set(RAW_EDITORIALS.map(e => e.theme).filter(Boolean))).sort();

            let html = `
                <button onclick="selectTheme('ALL')" class="text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                    state.selectedTheme === 'ALL' 
                        ? 'text-white bg-indigo-600 border-indigo-600' 
                        : 'hover:opacity-85'
                }" style="${state.selectedTheme === 'ALL' ? '' : 'background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);'}">All Themes</button>
            `;

            allThemes.forEach(th => {
                const isSelected = state.selectedTheme === th;
                html += `
                    <button onclick="selectTheme('${th}')" class="text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                        isSelected 
                            ? 'text-white bg-indigo-600 border-indigo-600' 
                            : 'hover:opacity-85'
                    }" style="${isSelected ? '' : 'background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);'}">${th}</button>
                `;
            });

            container.innerHTML = html;
        }

        function renderScopePills() {
            const container = document.getElementById('scopePillsContainer');
            if (!container) return;
            const allScopes = Array.from(new Set(RAW_EDITORIALS.map(e => e.scope).filter(Boolean))).sort();

            let html = `
                <button onclick="selectScope('ALL')" class="text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                    state.selectedScope === 'ALL' 
                        ? 'text-white bg-indigo-600 border-indigo-600' 
                        : 'hover:opacity-85'
                }" style="${state.selectedScope === 'ALL' ? '' : 'background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);'}">All Scopes</button>
            `;

            allScopes.forEach(sc => {
                const isSelected = state.selectedScope === sc;
                html += `
                    <button onclick="selectScope('${sc}')" class="text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                        isSelected 
                            ? 'text-white bg-indigo-600 border-indigo-600' 
                            : 'hover:opacity-85'
                    }" style="${isSelected ? '' : 'background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);'}">${sc}</button>
                `;
            });

            container.innerHTML = html;
        }

        function selectDate(dateStr) {
            state.selectedDate = dateStr;
            const dateSel = document.getElementById('mobileDateSelect');
            if (dateSel) dateSel.value = dateStr;
            renderDateList();
            renderSourceTabs();
            applyFilters();
        }

        function selectSource(src) {
            state.selectedSource = src;
            renderSourceTabs();
            applyFilters();
        }

        function selectTheme(theme) {
            state.selectedTheme = theme;
            const themeSel = document.getElementById('mobileThemeSelect');
            if (themeSel) themeSel.value = theme;
            renderThemePills();
            applyFilters();
        }

        function clearThemeFilter() {
            selectTheme('ALL');
        }

        function selectScope(sc) {
            state.selectedScope = sc;
            const scopeSel = document.getElementById('mobileScopeSelect');
            if (scopeSel) scopeSel.value = sc;
            renderScopePills();
            applyFilters();
        }

        function onSearchChange() {
            const val = document.getElementById('searchInput').value;
            state.searchQuery = val.trim().toLowerCase();
            document.getElementById('clearSearchBtn').classList.toggle('hidden', val.length === 0);
            applyFilters();
        }

        function clearSearch() {
            document.getElementById('searchInput').value = '';
            state.searchQuery = '';
            document.getElementById('clearSearchBtn').classList.add('hidden');
            applyFilters();
        }

        function resetAllFilters() {
            state.selectedSource = 'ALL';
            state.selectedTheme = 'ALL';
            state.selectedScope = 'ALL';
            clearSearch();

            const dateSel = document.getElementById('mobileDateSelect');
            if (dateSel) dateSel.value = state.selectedDate;
            const themeSel = document.getElementById('mobileThemeSelect');
            if (themeSel) themeSel.value = 'ALL';
            const scopeSel = document.getElementById('mobileScopeSelect');
            if (scopeSel) scopeSel.value = 'ALL';

            renderSourceTabs();
            renderThemePills();
            renderScopePills();
            applyFilters();
        }

        function toggleCard(id) {
            state.expandedCards[id] = !state.expandedCards[id];
            const section = document.getElementById(`details-${id}`);
            const btn = document.getElementById(`toggleBtn-${id}`);
            if (section && btn) {
                if (state.expandedCards[id]) {
                    section.classList.remove('hidden');
                    btn.innerHTML = '<span>Show Less</span> <i class="fa-solid fa-chevron-up text-xs"></i>';
                } else {
                    section.classList.add('hidden');
                    btn.innerHTML = '<span>Deep Analysis & Impact</span> <i class="fa-solid fa-chevron-down text-xs"></i>';
                }
            }
        }

        function copySummary(id) {
            const el = document.getElementById(`summaryText-${id}`);
            if (el) {
                navigator.clipboard.writeText(el.innerText).then(() => {
                    const tip = document.getElementById(`copyTip-${id}`);
                    tip.classList.remove('hidden');
                    setTimeout(() => tip.classList.add('hidden'), 2000);
                });
            }
        }

        function applyFilters() {
            const filtered = RAW_EDITORIALS.filter(item => {
                if (state.selectedDate !== 'ALL' && item.date !== state.selectedDate) return false;
                if (state.selectedSource !== 'ALL' && item.source !== state.selectedSource) return false;
                if (state.selectedTheme !== 'ALL' && item.theme !== state.selectedTheme) return false;
                if (state.selectedScope !== 'ALL' && item.scope !== state.selectedScope) return false;

                if (state.searchQuery) {
                    const q = state.searchQuery;
                    const matchOriginal = (item.original_title || '').toLowerCase().includes(q);
                    const matchEnglish = (item.english_title || '').toLowerCase().includes(q);
                    const matchSummary = (item.summary || '').toLowerCase().includes(q);
                    const matchTheme = (item.theme || '').toLowerCase().includes(q);
                    const matchBullets = Array.isArray(item.key_bullet_points) 
                        ? item.key_bullet_points.some(b => b.toLowerCase().includes(q))
                        : false;
                    const charStr = JSON.stringify(item.other_characteristics || '').toLowerCase();
                    const matchChar = charStr.includes(q);

                    if (!matchOriginal && !matchEnglish && !matchSummary && !matchTheme && !matchBullets && !matchChar) {
                        return false;
                    }
                }

                return true;
            });

            document.getElementById('filteredCount').innerText = filtered.length;
            renderArticles(filtered);
        }

        function renderArticles(items) {
            const container = document.getElementById('articlesList');
            const emptyState = document.getElementById('emptyState');

            if (items.length === 0) {
                container.innerHTML = '';
                emptyState.classList.remove('hidden');
                return;
            }

            emptyState.classList.add('hidden');

            let html = '';
            items.forEach((item, idx) => {
                const id = item.id || idx;
                const srcMeta = SOURCE_CONFIG[item.source] || {
                    label: item.source,
                    icon: 'fa-newspaper',
                    badgeBg: 'bg-slate-100 text-slate-800 border-slate-300 font-bold',
                    headerBorder: 'border-l-[4px] sm:border-l-[5px] border-slate-600'
                };

                const isTelugu = item.source === 'Eenadu';
                const isExpanded = !!state.expandedCards[id];

                // Bullet points HTML
                let bulletsHtml = '';
                if (Array.isArray(item.key_bullet_points) && item.key_bullet_points.length > 0) {
                    bulletsHtml = item.key_bullet_points.map(pt => `
                        <li class="flex items-start reading-bullet font-medium" style="color: var(--text-primary);">
                            <span class="inline-flex items-center justify-center w-5 h-5 rounded-full mr-2.5 sm:mr-3 mt-0.5 sm:mt-1 flex-shrink-0 text-xs font-bold" style="background-color: var(--accent-bg); color: var(--accent-primary);">
                                <i class="fa-solid fa-check text-[10px]"></i>
                            </span>
                            <span>${pt}</span>
                        </li>
                    `).join('');
                }

                // Characteristics & metadata unpack
                const chars = item.other_characteristics || {};
                const acts = chars.acts_and_articles_cited || [];
                const stats = chars.key_data_and_statistics || [];
                const examRel = chars.exam_policy_relevance || '';
                const tone = chars.tone || '';

                // Impact unpack
                const impact = item.impact || {};
                const shortImpact = impact.short_term || '';
                const longImpact = impact.long_term || '';

                // Build Impact Box HTML
                let impactHtml = '';
                if (shortImpact || longImpact) {
                    impactHtml = `
                        <div class="rounded-xl sm:rounded-2xl p-4 sm:p-5 border" style="background-color: var(--bg-subtle); border-color: var(--border-card);">
                            <h5 class="text-xs font-bold uppercase tracking-wider mb-2.5 sm:mb-3 flex items-center" style="color: var(--accent-primary);">
                                <i class="fa-solid fa-chart-line mr-2"></i> Strategic Impact Assessment
                            </h5>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 text-xs sm:text-sm">
                                ${shortImpact ? `
                                    <div class="card-surface p-3.5 sm:p-4 rounded-xl border">
                                        <span class="font-bold block mb-1 text-emerald-700">⚡ Short-Term Impact:</span>
                                        <p class="leading-relaxed font-medium" style="color: var(--text-secondary);">${shortImpact}</p>
                                    </div>
                                ` : ''}
                                ${longImpact ? `
                                    <div class="card-surface p-3.5 sm:p-4 rounded-xl border">
                                        <span class="font-bold block mb-1 text-indigo-700">🌐 Long-Term / Structural:</span>
                                        <p class="leading-relaxed font-medium" style="color: var(--text-secondary);">${longImpact}</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }

                html += `
                    <article class="card-surface rounded-xl sm:rounded-2xl border transition duration-200 overflow-hidden ${srcMeta.headerBorder}">
                        
                        <!-- Top Metadata Header -->
                        <div class="p-4 sm:p-7 pb-3 sm:pb-4 border-b" style="border-color: var(--border-subtle);">
                            <div class="flex flex-wrap items-center justify-between gap-2 sm:gap-3 mb-2.5 sm:mb-3.5">
                                
                                <div class="flex flex-wrap items-center gap-1.5 sm:gap-2">
                                    <span class="inline-flex items-center px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-lg text-xs border ${srcMeta.badgeBg}">
                                        <i class="fa-solid ${srcMeta.icon} mr-1 text-xs"></i> ${srcMeta.label}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 sm:py-1 rounded-lg text-xs font-semibold border" style="background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);">
                                        <i class="fa-regular fa-calendar mr-1 text-xs"></i> ${item.date}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 sm:py-1 rounded-lg text-xs font-bold border" style="background-color: var(--accent-bg); color: var(--accent-primary); border-color: var(--accent-border);">
                                        ${item.theme}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 sm:py-1 rounded-lg text-xs font-semibold border" style="background-color: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-card);">
                                        <i class="fa-solid fa-location-dot mr-1 text-xs"></i> ${item.scope || 'National'}
                                    </span>
                                </div>

                                <div class="flex items-center space-x-1.5 sm:space-x-2.5">
                                    <button onclick="copySummary(${id})" class="p-1.5 sm:p-2 rounded-lg border transition relative hover:opacity-80" style="background-color: var(--bg-subtle); border-color: var(--border-card); color: var(--text-secondary);" title="Copy Summary Text">
                                        <i class="fa-regular fa-copy text-xs sm:text-sm"></i>
                                        <span id="copyTip-${id}" class="hidden absolute -bottom-8 right-0 bg-slate-900 text-white text-xs px-2 py-0.5 rounded shadow z-10 whitespace-nowrap">Copied!</span>
                                    </button>
                                    <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center space-x-1 px-2.5 sm:px-3.5 py-1 sm:py-2 text-xs sm:text-sm font-bold rounded-xl transition border hover:opacity-85" style="background-color: var(--bg-subtle); color: var(--text-primary); border-color: var(--border-card);">
                                        <span>Original</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px] sm:text-xs"></i>
                                    </a>
                                </div>

                            </div>

                            <!-- Editorial Headlines -->
                            <div class="mt-1 sm:mt-2">
                                ${isTelugu ? `
                                    <h3 class="card-headline font-bold telugu-text mb-1" style="color: var(--text-primary);">
                                        ${item.original_title}
                                    </h3>
                                    <h4 class="text-xs sm:text-base font-semibold flex items-baseline flex-wrap" style="color: var(--text-secondary);">
                                        <span class="text-[10px] sm:text-xs font-bold uppercase tracking-wider mr-1.5 text-indigo-600">[Translation]</span>
                                        ${item.english_title}
                                    </h4>
                                ` : `
                                    <h3 class="card-headline font-bold" style="color: var(--text-primary);">
                                        ${item.english_title || item.original_title}
                                    </h3>
                                `}
                            </div>
                        </div>

                        <!-- Core Content Body -->
                        <div class="p-4 sm:p-7 space-y-4 sm:space-y-6">
                            
                            <!-- Executive Summary Highlight Box -->
                            <div class="rounded-xl sm:rounded-2xl p-4 sm:p-6 border" style="background-color: var(--bg-subtle); border-color: var(--border-card);">
                                <h5 class="text-xs font-bold uppercase tracking-wider mb-2 flex items-center" style="color: var(--accent-primary);">
                                    <i class="fa-solid fa-quote-left mr-2"></i> Executive Summary
                                </h5>
                                <p id="summaryText-${id}" class="reading-summary font-normal leading-relaxed" style="color: var(--text-primary);">
                                    ${item.summary}
                                </p>
                            </div>

                            <!-- Key Analytical Takeaways -->
                            ${bulletsHtml ? `
                                <div>
                                    <h5 class="text-xs font-bold uppercase tracking-wider mb-2.5 sm:mb-3.5 flex items-center" style="color: var(--text-muted);">
                                        <i class="fa-solid fa-list-check mr-2 text-emerald-600"></i> Crucial Takeaways & Arguments
                                    </h5>
                                    <ul class="space-y-2.5 sm:space-y-3.5 pl-0.5">
                                        ${bulletsHtml}
                                    </ul>
                                </div>
                            ` : ''}

                            <!-- Expandable Deep Analysis & Characteristics Section -->
                            <div id="details-${id}" class="${isExpanded ? '' : 'hidden'} space-y-4 sm:space-y-5 pt-3 sm:pt-4 border-t" style="border-color: var(--border-subtle);">
                                
                                <!-- Impact Matrix -->
                                ${impactHtml}

                                <!-- Characteristics & Acts Grid -->
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4 text-xs sm:text-sm">
                                    
                                    <!-- Tone & Stance -->
                                    <div class="card-surface p-3.5 sm:p-4 rounded-xl border">
                                        <span class="font-bold block mb-1" style="color: var(--text-secondary);">
                                            <i class="fa-solid fa-scale-balanced mr-1 text-indigo-500"></i> Editorial Tone:
                                        </span>
                                        <span class="inline-block px-2.5 py-1 rounded-lg text-xs font-bold border" style="background-color: var(--bg-subtle); color: var(--text-primary); border-color: var(--border-card);">
                                            ${tone || 'Analytical'}
                                        </span>
                                    </div>

                                    <!-- Acts / Articles Cited -->
                                    <div class="card-surface p-3.5 sm:p-4 rounded-xl border">
                                        <span class="font-bold block mb-1" style="color: var(--text-secondary);">
                                            <i class="fa-solid fa-gavel mr-1 text-indigo-500"></i> Constitutional / Legal Citations:
                                        </span>
                                        <div class="flex flex-wrap gap-1.5">
                                            ${Array.isArray(acts) && acts.length > 0 ? acts.map(a => `
                                                <span class="px-2 py-0.5 rounded text-xs font-bold font-mono border" style="background-color: var(--accent-bg); color: var(--accent-primary); border-color: var(--accent-border);">${a}</span>
                                            `).join('') : '<span class="text-xs italic" style="color: var(--text-muted);">None specifically cited</span>'}
                                        </div>
                                    </div>

                                    <!-- Exam / Policy Relevance -->
                                    <div class="card-surface p-3.5 sm:p-4 rounded-xl border">
                                        <span class="font-bold block mb-1" style="color: var(--text-secondary);">
                                            <i class="fa-solid fa-graduation-cap mr-1 text-indigo-500"></i> Exam / Syllabus Relevance:
                                        </span>
                                        <span class="font-medium text-xs sm:text-sm leading-relaxed" style="color: var(--text-primary);">${examRel || 'General Governance / GS Paper'}</span>
                                    </div>

                                </div>

                                <!-- Key Data & Statistics -->
                                ${Array.isArray(stats) && stats.length > 0 ? `
                                    <div class="card-surface p-3.5 sm:p-5 rounded-xl border text-xs sm:text-sm">
                                        <span class="font-bold block mb-1.5 sm:mb-2 text-amber-800">
                                            <i class="fa-solid fa-chart-pie mr-1 text-amber-600"></i> Cited Statistics & Key Data Points:
                                        </span>
                                        <div class="flex flex-wrap gap-2">
                                            ${stats.map(s => `
                                                <span class="inline-flex items-center px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-lg font-mono text-xs font-bold border bg-amber-50 text-amber-900 border-amber-200">
                                                    📊 ${s}
                                                </span>
                                            `).join('')}
                                        </div>
                                    </div>
                                ` : ''}

                            </div>

                            <!-- Card Footer Toggle -->
                            <div class="pt-2.5 sm:pt-3 flex items-center justify-between border-t" style="border-color: var(--border-subtle);">
                                <button 
                                    id="toggleBtn-${id}" 
                                    onclick="toggleCard(${id})" 
                                    class="text-xs sm:text-sm font-bold transition flex items-center space-x-1.5 py-1 px-2.5 sm:px-3 rounded-lg border hover:opacity-85"
                                    style="background-color: var(--bg-subtle); color: var(--accent-primary); border-color: var(--border-card);"
                                >
                                    <span>${isExpanded ? 'Show Less' : 'Deep Analysis & Impact'}</span>
                                    <i class="fa-solid ${isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'} text-xs"></i>
                                </button>
                                
                                <span class="text-xs font-mono font-medium" style="color: var(--text-muted);">Article #${id}</span>
                            </div>

                        </div>

                    </article>
                `;
            });

            container.innerHTML = html;
        }

        // Initialize on page load
        window.onload = function() {
            setTheme(state.theme);
            setFontScale(state.fontScale);
            updateStats();
            renderMobileDropdowns();
            renderDateList();
            renderSourceTabs();
            renderThemePills();
            renderScopePills();
            applyFilters();
        };
    </script>
</body>
</html>
"""

def generate_static_site(output_path: str = OUTPUT_HTML_PATH, db_path: str = DEFAULT_DB_PATH) -> str:
    """Queries DB and compiles index.html."""
    editorials = get_all_editorials(db_path)
    dates = get_available_dates(db_path)
    
    processed_items = []
    for item in editorials:
        d = dict(item)
        d["key_bullet_points"] = parse_field(d.get("key_bullet_points"), [])
        d["impact"] = parse_field(d.get("impact"), {})
        d["other_characteristics"] = parse_field(d.get("other_characteristics"), {})
        processed_items.append(d)

    editorials_json = json.dumps(processed_items, ensure_ascii=False)
    dates_json = json.dumps(dates, ensure_ascii=False)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = HTML_TEMPLATE.replace("__EDITORIALS_JSON__", editorials_json)
    html_content = html_content.replace("__DATES_JSON__", dates_json)
    html_content = html_content.replace("__GENERATED_AT__", generated_at)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Site generated successfully: {output_path} (Articles: {len(editorials)}, Dates: {len(dates)})")
    return output_path

if __name__ == "__main__":
    generate_static_site()
