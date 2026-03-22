# Page Monitor

This is a small Python script that checks a webpage for changes every 60 seconds.

## Files

- `monitor_page.py`: the main script
- `requirements.txt`: required Python packages

## Setup

Open PowerShell in this folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python monitor_page.py
```

Stop it any time with `Ctrl + C`.

## Customize

Edit `monitor_page.py` to change:

- `URL` for the page you want to monitor
- `CHECK_INTERVAL` for how often it checks
- `CSS_SELECTOR` if you only want to monitor one part of the page
