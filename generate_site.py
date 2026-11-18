#!/usr/bin/env python3
"""
generate_site.py
Generates a modern, fast, responsive standalone static dashboard (index.html)
from SQLite database (editorials.db) with multi-dimensional filtering
(day-wise, source-wise, theme, and live search).
Can be opened directly in any browser (no web server / port required).
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
    <title>Daily Editorial Aggregator & Analysis Dashboard</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Google Fonts: Inter & Noto Sans Telugu -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+Telugu:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        telugu: ['Noto Sans Telugu', 'sans-serif'],
                    },
                    colors: {
                        brand: {
                            eenadu: '#B91C1C',
                            eenaduBg: '#FEF2F2',
                            hindu: '#0F172A',
                            hinduBg: '#F8FAFC',
                            express: '#C2410C',
                            expressBg: '#FFF7ED',
                            pib: '#0D9488',
                            pibBg: '#F0FDFA',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        .telugu-text {
            font-family: 'Noto Sans Telugu', sans-serif;
        }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased font-sans min-h-screen flex flex-col">

    <!-- Top Navigation Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <!-- Brand Title -->
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
                        <i class="fa-solid fa-newspaper text-lg"></i>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h1 class="text-lg font-bold text-slate-900 tracking-tight">Editorial Intellect</h1>
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span> Standalone App
                            </span>
                        </div>
                        <p class="text-xs text-slate-500">Daily Multi-Source Editorial Aggregator & Analytical Synthesis</p>
                    </div>
                </div>

                <!-- Header Actions & Meta -->
                <div class="flex items-center space-x-4">
                    <div class="hidden md:flex flex-col text-right">
                        <span class="text-xs font-medium text-slate-700" id="currentDateDisplay">Loading date...</span>
                        <span class="text-[10px] text-slate-400">Compiled: __GENERATED_AT__</span>
                    </div>
                    <button onclick="window.location.reload()" class="p-2 text-slate-500 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition" title="Reload page">
                        <i class="fa-solid fa-rotate text-sm"></i>
                    </button>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1">
        
        <!-- Summary Stat Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
                <div class="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-lg">
                    <i class="fa-solid fa-file-lines"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-slate-900" id="statTotalArticles">0</div>
                    <div class="text-xs text-slate-500">Editorials Analyzed</div>
                </div>
            </div>

            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
                <div class="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center font-bold text-lg">
                    <i class="fa-solid fa-language"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-slate-900" id="statEenaduCount">0</div>
                    <div class="text-xs text-slate-500">Eenadu (తెలుగు)</div>
                </div>
            </div>

            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
                <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg">
                    <i class="fa-solid fa-layer-group"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-slate-900" id="statEnglishCount">0</div>
                    <div class="text-xs text-slate-500">National / Official</div>
                </div>
            </div>

            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-3">
                <div class="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold text-lg">
                    <i class="fa-solid fa-shapes"></i>
                </div>
                <div>
                    <div class="text-2xl font-bold text-slate-900" id="statThemesCount">0</div>
                    <div class="text-xs text-slate-500">Policy Themes</div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            <!-- Left Sidebar: Filters & Date Navigator -->
            <aside class="lg:col-span-1 space-y-6">
                
                <!-- Day-Wise Date Navigator -->
                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
                        <span><i class="fa-regular fa-calendar-days mr-1.5 text-indigo-500"></i> Date Archive</span>
                        <span class="text-[10px] text-slate-400 font-normal" id="dateArchiveCount"></span>
                    </h2>
                    
                    <div class="space-y-1" id="dateListContainer">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Theme Filter -->
                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
                        <span><i class="fa-solid fa-tags mr-1.5 text-indigo-500"></i> Filter by Theme</span>
                        <button onclick="clearThemeFilter()" class="text-[10px] text-indigo-600 hover:underline">Reset</button>
                    </h2>
                    
                    <div class="flex flex-wrap gap-1.5" id="themePillsContainer">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Scope Filter -->
                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                        <i class="fa-solid fa-globe mr-1.5 text-indigo-500"></i> Scope
                    </h2>
                    <div class="flex flex-wrap gap-1.5" id="scopePillsContainer">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Quick Tips for UPSC / Policy Aspirants -->
                <div class="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 rounded-xl p-4 text-xs text-indigo-900">
                    <div class="font-semibold mb-1 flex items-center">
                        <i class="fa-solid fa-lightbulb text-amber-500 mr-1.5"></i> Exam & Policy Utility
                    </div>
                    <p class="text-indigo-700 leading-relaxed">
                        Every editorial is analyzed for constitutional articles, statutory acts, economic data, and civil services syllabus mapping.
                    </p>
                </div>

            </aside>

            <!-- Main Content Area -->
            <main class="lg:col-span-3 space-y-5">
                
                <!-- Filter Controls Bar -->
                <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-4">
                    
                    <!-- Search Input -->
                    <div class="relative">
                        <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3 text-slate-400 text-sm"></i>
                        <input 
                            type="text" 
                            id="searchInput" 
                            oninput="onSearchChange()"
                            placeholder="Search editorials, keywords, Telugu terms (e.g., రాజ్యాంగం), Acts, or GDP..." 
                            class="w-full pl-10 pr-10 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
                        />
                        <button id="clearSearchBtn" onclick="clearSearch()" class="hidden absolute right-3 top-2.5 text-slate-400 hover:text-slate-600">
                            <i class="fa-solid fa-circle-xmark text-sm"></i>
                        </button>
                    </div>

                    <!-- Source-Wise Navigation Tabs -->
                    <div class="flex items-center overflow-x-auto space-x-2 pb-1 border-b border-slate-100 custom-scrollbar" id="sourceTabsContainer">
                        <!-- Populated by JS -->
                    </div>

                    <!-- Active Filters Badge Row -->
                    <div class="flex items-center justify-between text-xs text-slate-500 pt-1" id="filterStatsBar">
                        <div class="flex items-center space-x-2">
                            <span>Showing <strong class="text-slate-900" id="filteredCount">0</strong> articles</span>
                            <span id="activeFilterTags" class="flex items-center space-x-1.5"></span>
                        </div>
                        <button onclick="resetAllFilters()" class="text-slate-400 hover:text-indigo-600 transition flex items-center space-x-1">
                            <i class="fa-solid fa-filter-circle-xmark"></i>
                            <span>Clear Filters</span>
                        </button>
                    </div>

                </div>

                <!-- Articles Grid Container -->
                <div id="articlesList" class="space-y-4">
                    <!-- Populated dynamically by JS -->
                </div>

                <!-- Empty State -->
                <div id="emptyState" class="hidden bg-white border border-dashed border-slate-300 rounded-2xl p-12 text-center">
                    <div class="w-16 h-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400 text-2xl mb-4">
                        <i class="fa-solid fa-folder-open"></i>
                    </div>
                    <h3 class="text-base font-semibold text-slate-800 mb-1">No Editorials Match Your Criteria</h3>
                    <p class="text-xs text-slate-500 max-w-sm mx-auto mb-4">Try clearing some filters or searching for alternative topics or keywords.</p>
                    <button onclick="resetAllFilters()" class="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition">
                        Reset All Filters
                    </button>
                </div>

            </main>
        </div>

    </div>

    <!-- Footer -->
    <footer class="bg-white border-t border-slate-200 py-6 mt-12 text-xs text-slate-500">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex items-center space-x-2">
                <span class="font-semibold text-slate-700">Editorial Intellect Agent</span>
                <span>•</span>
                <span>Automated Daily Digest (11:30 AM IST)</span>
            </div>
            <div class="flex items-center space-x-4">
                <span>Sources: Eenadu • The Hindu • Indian Express • PIB</span>
                <span>•</span>
                <span class="text-indigo-600 font-medium">Antigravity 2.0</span>
            </div>
        </div>
    </footer>

    <!-- Application Script & Data Store -->
    <script>
        // Injected Database Records
        const RAW_EDITORIALS = __EDITORIALS_JSON__;
        const AVAILABLE_DATES = __DATES_JSON__;

        // State Store
        let state = {
            selectedDate: 'ALL',
            selectedSource: 'ALL',
            selectedTheme: 'ALL',
            selectedScope: 'ALL',
            searchQuery: '',
            expandedCards: {}
        };

        // Source Metadata Configuration
        const SOURCE_CONFIG = {
            'Eenadu': {
                label: 'Eenadu (తెలుగు)',
                icon: 'fa-feather-pointed',
                badgeBg: 'bg-rose-50 text-rose-700 border-rose-200',
                headerBorder: 'border-l-4 border-rose-600',
                tag: 'EENADU'
            },
            'The Hindu': {
                label: 'The Hindu',
                icon: 'fa-book-open',
                badgeBg: 'bg-slate-100 text-slate-800 border-slate-300',
                headerBorder: 'border-l-4 border-slate-800',
                tag: 'THE HINDU'
            },
            'Indian Express': {
                label: 'The Indian Express',
                icon: 'fa-bolt',
                badgeBg: 'bg-orange-50 text-orange-700 border-orange-200',
                headerBorder: 'border-l-4 border-orange-600',
                tag: 'INDIAN EXPRESS'
            },
            'PIB': {
                label: 'Official / PIB',
                icon: 'fa-landmark',
                badgeBg: 'bg-teal-50 text-teal-700 border-teal-200',
                headerBorder: 'border-l-4 border-teal-600',
                tag: 'PIB / GOVT'
            }
        };

        // Initialization
        document.addEventListener('DOMContentLoaded', () => {
            if (AVAILABLE_DATES.length > 0) {
                // Default to latest date
                state.selectedDate = AVAILABLE_DATES[0];
            }
            updateHeaderDate();
            renderDateList();
            renderSourceTabs();
            renderThemePills();
            renderScopePills();
            applyFilters();
            calculateSummaryStats();
        });

        function updateHeaderDate() {
            const el = document.getElementById('currentDateDisplay');
            if (state.selectedDate && state.selectedDate !== 'ALL') {
                const parts = state.selectedDate.split('-');
                if (parts.length === 3) {
                    const d = new Date(parts[0], parts[1] - 1, parts[2]);
                    el.innerText = d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' });
                } else {
                    el.innerText = state.selectedDate;
                }
            } else {
                el.innerText = 'All Dates Archive';
            }
        }

        function calculateSummaryStats() {
            document.getElementById('statTotalArticles').innerText = RAW_EDITORIALS.length;
            const eenaduCount = RAW_EDITORIALS.filter(e => e.source === 'Eenadu').length;
            const englishCount = RAW_EDITORIALS.length - eenaduCount;
            document.getElementById('statEenaduCount').innerText = eenaduCount;
            document.getElementById('statEnglishCount').innerText = englishCount;

            const themes = new Set(RAW_EDITORIALS.map(e => e.theme).filter(Boolean));
            document.getElementById('statThemesCount').innerText = themes.size;
        }

        function renderDateList() {
            const container = document.getElementById('dateListContainer');
            document.getElementById('dateArchiveCount').innerText = `${AVAILABLE_DATES.length} dates`;

            let html = `
                <button onclick="selectDate('ALL')" class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition flex items-center justify-between ${state.selectedDate === 'ALL' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}">
                    <span><i class="fa-solid fa-calendar-check mr-2 text-slate-400"></i> All Available Dates</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-200 text-slate-700">${RAW_EDITORIALS.length}</span>
                </button>
            `;

            AVAILABLE_DATES.forEach((dateStr, idx) => {
                const count = RAW_EDITORIALS.filter(e => e.date === dateStr).length;
                const isSelected = state.selectedDate === dateStr;
                let label = dateStr;
                if (idx === 0) label += " (Latest)";

                html += `
                    <button onclick="selectDate('${dateStr}')" class="w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition flex items-center justify-between ${isSelected ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-700 hover:bg-slate-100'}">
                        <span><i class="fa-regular fa-calendar mr-2 ${isSelected ? 'text-white' : 'text-slate-400'}"></i> ${label}</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded-full ${isSelected ? 'bg-indigo-700 text-indigo-100' : 'bg-slate-100 text-slate-600'}">${count}</span>
                    </button>
                `;
            });

            container.innerHTML = html;
        }

        function renderSourceTabs() {
            const container = document.getElementById('sourceTabsContainer');
            const sources = ['ALL', 'Eenadu', 'The Hindu', 'Indian Express', 'PIB'];

            let html = '';
            sources.forEach(src => {
                const isAll = src === 'ALL';
                const count = isAll 
                    ? (state.selectedDate === 'ALL' ? RAW_EDITORIALS.length : RAW_EDITORIALS.filter(e => e.date === state.selectedDate).length)
                    : RAW_EDITORIALS.filter(e => e.source === src && (state.selectedDate === 'ALL' || e.date === state.selectedDate)).length;
                
                const isSelected = state.selectedSource === src;
                const label = isAll ? 'All Sources' : (SOURCE_CONFIG[src]?.label || src);
                const icon = isAll ? 'fa-globe' : (SOURCE_CONFIG[src]?.icon || 'fa-newspaper');

                html += `
                    <button onclick="selectSource('${src}')" class="whitespace-nowrap px-3.5 py-2 rounded-lg text-xs font-medium transition flex items-center space-x-2 border ${
                        isSelected 
                            ? 'bg-slate-900 text-white border-slate-900 shadow-sm' 
                            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:text-slate-900'
                    }">
                        <i class="fa-solid ${icon} ${isSelected ? 'text-indigo-400' : 'text-slate-400'}"></i>
                        <span>${label}</span>
                        <span class="px-1.5 py-0.2 rounded-full text-[10px] ${
                            isSelected ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'
                        }">${count}</span>
                    </button>
                `;
            });

            container.innerHTML = html;
        }

        function renderThemePills() {
            const container = document.getElementById('themePillsContainer');
            const allThemes = Array.from(new Set(RAW_EDITORIALS.map(e => e.theme).filter(Boolean))).sort();

            let html = `
                <button onclick="selectTheme('ALL')" class="text-xs px-2.5 py-1 rounded-md border transition ${
                    state.selectedTheme === 'ALL' 
                        ? 'bg-indigo-600 text-white border-indigo-600 font-medium' 
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }">All Themes</button>
            `;

            allThemes.forEach(th => {
                const isSelected = state.selectedTheme === th;
                html += `
                    <button onclick="selectTheme('${th}')" class="text-xs px-2.5 py-1 rounded-md border transition ${
                        isSelected 
                            ? 'bg-indigo-600 text-white border-indigo-600 font-medium' 
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }">${th}</button>
                `;
            });

            container.innerHTML = html;
        }

        function renderScopePills() {
            const container = document.getElementById('scopePillsContainer');
            const allScopes = Array.from(new Set(RAW_EDITORIALS.map(e => e.scope).filter(Boolean))).sort();

            let html = `
                <button onclick="selectScope('ALL')" class="text-xs px-2.5 py-1 rounded-md border transition ${
                    state.selectedScope === 'ALL' 
                        ? 'bg-indigo-600 text-white border-indigo-600 font-medium' 
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }">All Scopes</button>
            `;

            allScopes.forEach(sc => {
                const isSelected = state.selectedScope === sc;
                html += `
                    <button onclick="selectScope('${sc}')" class="text-xs px-2.5 py-1 rounded-md border transition ${
                        isSelected 
                            ? 'bg-indigo-600 text-white border-indigo-600 font-medium' 
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }">${sc}</button>
                `;
            });

            container.innerHTML = html;
        }

        function selectDate(dateStr) {
            state.selectedDate = dateStr;
            updateHeaderDate();
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
            renderThemePills();
            applyFilters();
        }

        function clearThemeFilter() {
            selectTheme('ALL');
        }

        function selectScope(sc) {
            state.selectedScope = sc;
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
                    btn.innerHTML = '<span>Deep Analysis & Characteristics</span> <i class="fa-solid fa-chevron-down text-xs"></i>';
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
                // Date check
                if (state.selectedDate !== 'ALL' && item.date !== state.selectedDate) return false;
                
                // Source check
                if (state.selectedSource !== 'ALL' && item.source !== state.selectedSource) return false;

                // Theme check
                if (state.selectedTheme !== 'ALL' && item.theme !== state.selectedTheme) return false;

                // Scope check
                if (state.selectedScope !== 'ALL' && item.scope !== state.selectedScope) return false;

                // Search query check
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
                    badgeBg: 'bg-slate-100 text-slate-800 border-slate-200',
                    headerBorder: 'border-l-4 border-slate-600',
                    tag: item.source
                };

                const isTelugu = item.source === 'Eenadu';
                const isExpanded = !!state.expandedCards[id];

                // Bullet points HTML
                let bulletsHtml = '';
                if (Array.isArray(item.key_bullet_points) && item.key_bullet_points.length > 0) {
                    bulletsHtml = item.key_bullet_points.map(pt => `
                        <li class="flex items-start text-xs text-slate-700 leading-relaxed">
                            <i class="fa-solid fa-circle-check text-indigo-500 mt-1 mr-2 flex-shrink-0 text-[10px]"></i>
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
                        <div class="bg-indigo-50/50 rounded-xl p-4 border border-indigo-100/60">
                            <h5 class="text-xs font-bold text-indigo-900 uppercase tracking-wider mb-2 flex items-center">
                                <i class="fa-solid fa-chart-line text-indigo-600 mr-1.5"></i> Impact Assessment
                            </h5>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                ${shortImpact ? `
                                    <div class="bg-white p-3 rounded-lg border border-indigo-100">
                                        <span class="font-semibold text-slate-800 block mb-1">⚡ Short-Term Impact:</span>
                                        <p class="text-slate-600 leading-relaxed">${shortImpact}</p>
                                    </div>
                                ` : ''}
                                ${longImpact ? `
                                    <div class="bg-white p-3 rounded-lg border border-indigo-100">
                                        <span class="font-semibold text-slate-800 block mb-1">🌐 Long-Term / Structural:</span>
                                        <p class="text-slate-600 leading-relaxed">${longImpact}</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }

                html += `
                    <article class="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition duration-200 overflow-hidden ${srcMeta.headerBorder}">
                        
                        <!-- Top Metadata Header -->
                        <div class="p-5 pb-3 border-b border-slate-100">
                            <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                                
                                <div class="flex items-center space-x-2">
                                    <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${srcMeta.badgeBg}">
                                        <i class="fa-solid ${srcMeta.icon} mr-1.5 text-[11px]"></i> ${srcMeta.label}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">
                                        <i class="fa-regular fa-calendar mr-1 text-[10px]"></i> ${item.date}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                                        ${item.theme}
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-50 text-slate-600 border border-slate-200">
                                        <i class="fa-solid fa-location-dot mr-1 text-[10px] text-slate-400"></i> ${item.scope}
                                    </span>
                                </div>

                                <div class="flex items-center space-x-2">
                                    <button onclick="copySummary(${id})" class="p-1.5 text-slate-400 hover:text-indigo-600 rounded transition relative" title="Copy Summary">
                                        <i class="fa-regular fa-copy text-sm"></i>
                                        <span id="copyTip-${id}" class="hidden absolute -bottom-7 right-0 bg-slate-800 text-white text-[10px] px-2 py-0.5 rounded shadow z-10 whitespace-nowrap">Copied!</span>
                                    </button>
                                    <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center space-x-1.5 px-3 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition border border-slate-200">
                                        <span>Read Original</span>
                                        <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                                    </a>
                                </div>

                            </div>

                            <!-- Headlines -->
                            <div>
                                ${isTelugu ? `
                                    <h3 class="text-lg font-bold text-slate-900 telugu-text leading-snug mb-1">
                                        ${item.original_title}
                                    </h3>
                                    <h4 class="text-sm font-semibold text-slate-600 flex items-center">
                                        <span class="text-xs font-normal uppercase tracking-wider text-slate-400 mr-2">[Eng Translation]</span>
                                        ${item.english_title}
                                    </h4>
                                ` : `
                                    <h3 class="text-lg font-bold text-slate-900 leading-snug">
                                        ${item.english_title || item.original_title}
                                    </h3>
                                `}
                            </div>
                        </div>

                        <!-- Core Content Body -->
                        <div class="p-5 space-y-4">
                            
                            <!-- Executive Summary -->
                            <div>
                                <h5 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center">
                                    <i class="fa-solid fa-quote-left text-indigo-500 mr-1.5"></i> Executive Summary
                                </h5>
                                <p id="summaryText-${id}" class="text-sm text-slate-700 leading-relaxed font-normal bg-slate-50 p-3.5 rounded-lg border border-slate-100">
                                    ${item.summary}
                                </p>
                            </div>

                            <!-- Key Bullet Points Takeaways -->
                            ${bulletsHtml ? `
                                <div>
                                    <h5 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center">
                                        <i class="fa-solid fa-list-check text-indigo-500 mr-1.5"></i> Key Analytical Takeaways
                                    </h5>
                                    <ul class="space-y-1.5 pl-1">
                                        ${bulletsHtml}
                                    </ul>
                                </div>
                            ` : ''}

                            <!-- Expandable Deep Analysis & Characteristics Section -->
                            <div id="details-${id}" class="${isExpanded ? '' : 'hidden'} space-y-4 pt-3 border-t border-slate-100">
                                
                                <!-- Impact Matrix -->
                                ${impactHtml}

                                <!-- Characteristics & Acts Grid -->
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                                    
                                    <!-- Tone & Stance -->
                                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                                        <span class="font-semibold text-slate-700 block mb-1">
                                            <i class="fa-solid fa-scale-balanced mr-1 text-slate-400"></i> Editorial Tone:
                                        </span>
                                        <span class="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-white border border-slate-200 text-slate-800">
                                            ${tone || 'Analytical'}
                                        </span>
                                    </div>

                                    <!-- Acts / Articles Cited -->
                                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                                        <span class="font-semibold text-slate-700 block mb-1">
                                            <i class="fa-solid fa-gavel mr-1 text-slate-400"></i> Constitutional / Legal Citations:
                                        </span>
                                        <div class="flex flex-wrap gap-1">
                                            ${Array.isArray(acts) && acts.length > 0 ? acts.map(a => `
                                                <span class="px-1.5 py-0.5 bg-white border border-slate-200 text-slate-700 rounded text-[10px] font-mono">${a}</span>
                                            `).join('') : '<span class="text-slate-400 italic">None specifically cited</span>'}
                                        </div>
                                    </div>

                                    <!-- Exam / Policy Relevance -->
                                    <div class="bg-slate-50 p-3 rounded-lg border border-slate-200">
                                        <span class="font-semibold text-slate-700 block mb-1">
                                            <i class="fa-solid fa-graduation-cap mr-1 text-slate-400"></i> Policy / Exam Relevance:
                                        </span>
                                        <span class="text-slate-600 leading-relaxed">${examRel || 'General Governance / GS Paper'}</span>
                                    </div>

                                </div>

                                <!-- Key Data & Statistics -->
                                ${Array.isArray(stats) && stats.length > 0 ? `
                                    <div class="bg-amber-50/50 p-3 rounded-lg border border-amber-200/60 text-xs">
                                        <span class="font-semibold text-amber-900 block mb-1">
                                            <i class="fa-solid fa-chart-pie mr-1 text-amber-600"></i> Key Data & Statistics Cited:
                                        </span>
                                        <div class="flex flex-wrap gap-2">
                                            ${stats.map(s => `
                                                <span class="inline-flex items-center px-2 py-0.5 bg-white border border-amber-200 text-amber-900 rounded font-mono text-[11px]">
                                                    📊 ${s}
                                                </span>
                                            `).join('')}
                                        </div>
                                    </div>
                                ` : ''}

                            </div>

                            <!-- Card Footer Toggle -->
                            <div class="pt-2 flex items-center justify-between">
                                <button 
                                    id="toggleBtn-${id}" 
                                    onclick="toggleCard(${id})" 
                                    class="text-xs font-medium text-indigo-600 hover:text-indigo-800 transition flex items-center space-x-1.5 py-1 px-2 rounded-md hover:bg-indigo-50"
                                >
                                    <span>${isExpanded ? 'Show Less' : 'Deep Analysis & Characteristics'}</span>
                                    <i class="fa-solid ${isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'} text-xs"></i>
                                </button>
                                
                                <span class="text-[10px] text-slate-400 font-mono">ID: #${id}</span>
                            </div>

                        </div>

                    </article>
                `;
            });

            container.innerHTML = html;
        }
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
