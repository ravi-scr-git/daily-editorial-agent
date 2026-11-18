@echo off
REM Automated Daily Editorial Aggregator Runner (Unattended Auto Mode)
cd /d "D:\RAVI\daily-editorial-agent"
agy --mode auto --dangerously-skip-permissions -p "Run /editorial-digest to capture today's editorials from Eenadu, The Hindu, and official sources, store them in editorials.db, and rebuild index.html"
