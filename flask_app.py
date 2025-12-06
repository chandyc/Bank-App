import json
import os
from flask import Flask, request
from datetime import datetime

# Initialize Flask app (this creates our web application)
app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Required for sessions (not used yet, but good practice)

# File paths - these tell Python where to save your data
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "balances.json")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "balances.json.history")
FORECAST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast.json")

# ============================================================================
# ACCOUNT DEFINITIONS
# ============================================================================
# Each account has a name and a group letter:
# c = checking/credit cards
# b = bills (sub-category of checking)
# s = savings and assets
# r = retirement accounts

ACCOUNTS = [
    ("Bank", "c"),
    ("Rent (Credit)", "c"),
    ("Bills", "c"),
    ("Cash", "c"),
    ("Chase Card (Credit)", "c"),
    ("Capital One Card (Credit)", "c"),
    ("Discover Card (Credit)", "c"),
    ("Apple Card (Credit)", "c"),
    ("Amazon Card (Credit)", "c"),
    ("Amazon Refunds", "c"),
    ("GEICO", "b"),
    ("TXU", "b"),
    ("Spectrum", "b"),
    ("Washer", "b"),
    ("Car Note", "b"),
    ("Bank_savings", "s"),
    ("Stocks", "s"),
    ("IRA", "s"),
    ("Cash_savings", "s"),
    ("401k", "r"),
    ("India", "r")
]

# Create lists of account names by category (using list comprehension)
# This filters ACCOUNTS to get only names where group matches
BILLS = [name for name, group in ACCOUNTS if group == "b"]
CHECKS = [name for name, group in ACCOUNTS if group == "c" and name != "Bills"]
SAVES = [name for name, group in ACCOUNTS if group == "s"]
RETIRE = [name for name, group in ACCOUNTS if group == "r"]

# Credit card accounts that should display as negative values
# User enters positive amounts, but we'll display them as credits (negative)
CREDIT_CARDS = [
    "Chase Card (Credit)",
    "Capital One Card (Credit)",
    "Discover Card (Credit)",
    "Apple Card (Credit)",
    "Amazon Card (Credit)",
    "Bills"  # Bills are also credits (money owed)
]


# ============================================================================
# DATA FUNCTIONS
# ============================================================================

def load():
    """Load account balances from JSON file.
    If file doesn't exist or account is missing, default to 0."""
    
    # Start with all accounts set to 0
    defaults = {name: 0 for name, _ in ACCOUNTS}
    
    # If saved file exists, load it and merge with defaults
    # The ** syntax merges dictionaries (defaults first, then saved values override)
    if os.path.exists(DATA_FILE):
        saved = json.load(open(DATA_FILE))
        return {**defaults, **saved}
    
    return defaults


def load_history():
    """Load all saved snapshots from history file.
    Returns empty list if no history exists yet."""
    
    if os.path.exists(HISTORY_FILE):
        return json.load(open(HISTORY_FILE))
    return []


def save(balances):
    """Save current balances to JSON file.
    indent=4 makes the file human-readable."""
    
    json.dump(balances, open(DATA_FILE, 'w'), indent=4)


def save_snapshot(balances):
    """Add current balances to history with timestamp.
    This is how we track changes over time."""
    
    history = load_history()
    
    # Create snapshot with current time and all account balances
    snapshot = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **{name: balances[name] for name, _ in ACCOUNTS}
    }
    
    history.append(snapshot)
    json.dump(history, open(HISTORY_FILE, 'w'), indent=4)


def load_forecast_settings():
    """Load saved forecast settings (monthly contribution).
    Returns default of 0 if no settings file exists."""
    
    if os.path.exists(FORECAST_FILE):
        settings = json.load(open(FORECAST_FILE))
        return settings.get("monthly_contribution", 0)
    return 0


def save_forecast_settings(monthly_contribution):
    """Save forecast settings to file so they persist between sessions."""
    
    settings = {"monthly_contribution": monthly_contribution}
    json.dump(settings, open(FORECAST_FILE, 'w'), indent=4)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fmt(value):
    """Format a number as currency ($1,234.56)"""
    return "${:,.2f}".format(value)


def tot(account_names, balances):
    """Calculate total for a list of accounts.
    Example: tot(['Bank', 'Cash'], balances) adds those two accounts."""
    
    return sum(float(balances.get(name, 0)) for name in account_names)


def clean_name(name):
    """Make account names prettier for display.
    Removes (Credit) and fixes underscores."""
    
    return name.replace("(Credit)", "").replace("_savings", " Savings").replace("_", " ")


# ============================================================================
# HTML GENERATION
# ============================================================================

def get_html_header(title, active_page):
    """Generate the top part of every page with navigation.
    active_page controls which nav button is highlighted."""
    
    # Set which nav link gets the 'active' class
    balances_active = "active" if active_page == "balances" else ""
    history_active = "active" if active_page == "history" else ""
    forecast_active = "active" if active_page == "forecast" else ""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Mukunda · {title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        /* Reset & Base */
        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        :root {{
            --bg-dark: #0a0a0f;
            --bg-card: rgba(255, 255, 255, 0.03);
            --bg-card-hover: rgba(255, 255, 255, 0.06);
            --border: rgba(255, 255, 255, 0.08);
            --border-light: rgba(255, 255, 255, 0.12);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.6);
            --text-muted: rgba(255, 255, 255, 0.4);
            --accent: #00d4aa;
            --accent-glow: rgba(0, 212, 170, 0.3);
            --accent-soft: rgba(0, 212, 170, 0.15);
            --purple: #a855f7;
            --purple-soft: rgba(168, 85, 247, 0.15);
            --orange: #f97316;
            --orange-soft: rgba(249, 115, 22, 0.15);
            --red: #ef4444;
            --red-soft: rgba(239, 68, 68, 0.2);
        }}
        
        body {{
            font-family: 'DM Sans', -apple-system, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
            overflow-x: hidden;
        }}
        
        /* Animated gradient background */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0, 212, 170, 0.15), transparent),
                radial-gradient(ellipse 60% 40% at 80% 110%, rgba(168, 85, 247, 0.1), transparent),
                radial-gradient(ellipse 50% 30% at 50% 50%, rgba(249, 115, 22, 0.05), transparent);
            pointer-events: none;
            z-index: 0;
        }}
        
        /* Noise texture overlay */
        body::after {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
            opacity: 0.03;
            pointer-events: none;
            z-index: 0;
        }}
        
        /* Container */
        .container {{
            position: relative;
            z-index: 1;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 24px 80px;
        }}
        
        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 60px;
            animation: fadeDown 0.8s ease-out;
        }}
        
        @keyframes fadeDown {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .logo-icon {{
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, var(--accent), #00a080);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Instrument Serif', serif;
            font-size: 24px;
            font-weight: 400;
            color: var(--bg-dark);
            box-shadow: 0 8px 32px var(--accent-glow);
        }}
        
        .logo-text {{
            font-family: 'Instrument Serif', serif;
            font-size: 28px;
            font-weight: 400;
            letter-spacing: -0.02em;
        }}
        
        /* Navigation */
        nav {{
            display: flex;
            gap: 8px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 6px;
            backdrop-filter: blur(20px);
        }}
        
        nav a {{
            padding: 10px 20px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            border-radius: 10px;
            transition: all 0.3s ease;
        }}
        
        nav a:hover {{
            color: var(--text-primary);
            background: var(--bg-card-hover);
        }}
        
        nav a.active {{
            background: var(--text-primary);
            color: var(--bg-dark);
        }}
        
        /* Hero Section (Net Worth) */
        .hero {{
            text-align: center;
            margin-bottom: 60px;
            animation: fadeUp 0.8s ease-out 0.2s both;
        }}
        
        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .hero-label {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .hero-value {{
            font-family: 'Instrument Serif', serif;
            font-size: clamp(48px, 10vw, 80px);
            font-weight: 400;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.1;
        }}
        
        /* Card Grid */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        @media (max-width: 480px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Cards */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 28px;
            backdrop-filter: blur(20px);
            transition: all 0.4s ease;
            animation: fadeUp 0.6s ease-out both;
        }}
        
        .card:nth-child(1) {{ animation-delay: 0.3s; }}
        .card:nth-child(2) {{ animation-delay: 0.4s; }}
        .card:nth-child(3) {{ animation-delay: 0.5s; }}
        
        .card:hover {{
            border-color: var(--border-light);
            transform: translateY(-4px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .card-title {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .card-icon {{
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }}
        
        .card-icon.green {{ background: var(--accent-soft); }}
        .card-icon.purple {{ background: var(--purple-soft); }}
        .card-icon.orange {{ background: var(--orange-soft); }}
        
        .card-label {{
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .card-total {{
            font-family: 'Instrument Serif', serif;
            font-size: 28px;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }}
        
        /* Account Rows */
        .account-list {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            overflow-x: auto; /* Allow horizontal scroll on mobile */
        }}
        
        .account-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            transition: all 0.2s ease;
            min-width: fit-content; /* Prevent shrinking */
        }}
        
        .account-row:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .account-name {{
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
            white-space: nowrap; /* Prevent name wrapping */
            margin-right: 12px; /* Add spacing */
        }}
        
        .account-input {{
            width: 130px;
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 15px;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
            text-align: right;
            transition: all 0.3s ease;
        }}
        
        .account-input:focus {{
            outline: none;
            border-color: var(--accent);
            background: rgba(0, 212, 170, 0.05);
            box-shadow: 0 0 0 4px var(--accent-soft);
        }}
        
        .account-input[readonly] {{
            background: transparent;
            border-color: transparent;
            color: var(--text-muted);
        }}
        
        /* Credit card styling - show they're credits/debts */
        .account-row.credit-card .account-name::before {{
            content: '−';
            margin-right: 6px;
            color: var(--accent);
            font-weight: 700;
        }}
        
        /* Bills Toggle */
        .bills-toggle {{
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px dashed var(--border);
            border-radius: 12px;
            color: var(--text-secondary);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'DM Sans', sans-serif;
        }}
        
        .bills-toggle:hover {{
            background: rgba(255, 255, 255, 0.04);
            border-color: var(--border-light);
        }}
        
        .bills-toggle svg {{
            transition: transform 0.3s ease;
        }}
        
        .bills-toggle.open svg {{
            transform: rotate(180deg);
        }}
        
        .bills-content {{
            display: none;
            padding: 16px 0 0;
        }}
        
        .bills-content.show {{
            display: block;
            animation: slideDown 0.3s ease-out;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Save Button */
        .save-section {{
            display: flex;
            justify-content: center;
            padding-top: 20px;
            animation: fadeUp 0.6s ease-out 0.6s both;
        }}
        
        .save-btn {{
            padding: 18px 48px;
            background: linear-gradient(135deg, var(--accent), #00a080);
            border: none;
            border-radius: 16px;
            color: var(--bg-dark);
            font-size: 16px;
            font-weight: 700;
            font-family: 'DM Sans', sans-serif;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 32px var(--accent-glow);
        }}
        
        .save-btn:hover {{
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 12px 40px var(--accent-glow);
        }}
        
        .save-btn:active {{
            transform: translateY(0) scale(0.98);
        }}
        
        /* History Page */
        .history-header {{
            text-align: center;
            margin-bottom: 48px;
            animation: fadeUp 0.6s ease-out;
        }}
        
        .history-title {{
            font-family: 'Instrument Serif', serif;
            font-size: 40px;
            margin-bottom: 8px;
        }}
        
        .history-subtitle {{
            color: var(--text-muted);
            font-size: 15px;
        }}
        
        /* Chart Container */
        .chart-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 32px;
            backdrop-filter: blur(20px);
            margin-bottom: 32px;
            animation: fadeUp 0.6s ease-out 0.1s both;
            height: 400px;
            width: 100%;
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
            width: 100%; /* Force full width */
        }}
        
        @media (max-width: 968px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
                width: 100%; /* Maintain full width on mobile */
            }}
        }}
        
        .history-table-wrap {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 24px;
            overflow: hidden;
            backdrop-filter: blur(20px);
            animation: fadeUp 0.6s ease-out 0.2s both;
            overflow-x: auto; /* Enable horizontal scroll on mobile */
            -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
            width: 100%; /* Force full width */
        }}
        
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: auto; /* Allow table to resize properly */
        }}
        
        /* Only apply min-width on larger screens */
        @media (min-width: 641px) {{
            .history-table {{
                min-width: 600px;
            }}
        }}
        
        /* On mobile, remove min-width so table can expand to full card width */
        @media (max-width: 640px) {{
            .history-table {{
                min-width: 100%;
            }}
        }}
        
        .history-table th {{
            padding: 18px 20px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border);
        }}
        
        .history-table th:not(:first-child) {{
            text-align: right;
        }}
        
        .history-table td {{
            padding: 18px 20px;
            font-size: 14px;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
        }}
        
        .history-table td:not(:first-child) {{
            text-align: right;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
        }}
        
        .history-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .history-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        
        .history-date {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .history-total {{
            color: var(--accent) !important;
            font-weight: 600 !important;
        }}
        
        .delete-btn {{
            width: 32px;
            height: 32px;
            background: var(--red-soft);
            border: none;
            border-radius: 8px;
            color: var(--red);
            font-size: 18px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}
        
        .delete-btn:hover {{
            background: var(--red);
            color: white;
            transform: scale(1.1);
        }}
        
        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 80px 40px;
            animation: fadeUp 0.6s ease-out;
        }}
        
        .empty-icon {{
            font-size: 64px;
            margin-bottom: 24px;
            opacity: 0.3;
        }}
        
        .empty-text {{
            color: var(--text-muted);
            font-size: 16px;
            max-width: 300px;
            margin: 0 auto;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 24px 16px 60px;
            }}
            
            header {{
                flex-direction: column;
                gap: 20px;
            }}
            
            .hero {{
                margin-bottom: 40px;
            }}
            
            .hero-value {{
                font-size: 42px;
            }}
            
            .card {{
                padding: 20px;
            }}
            
            .card-total {{
                font-size: 24px;
            }}
            
            .account-input {{
                width: 110px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            
            .chart-container {{
                height: 300px;
                padding: 20px;
                width: 100%;
            }}
            
            .history-table {{
                font-size: 13px;
                min-width: 550px; /* Slightly smaller min-width for mobile */
            }}
            
            .history-table th,
            .history-table td {{
                padding: 14px 12px;
            }}
            
            /* Make amounts more compact on mobile */
            .history-table th:not(:first-child),
            .history-table td:not(:first-child) {{
                font-size: 12px;
            }}
            
            /* On small mobile screens, hide the middle columns */
            @media (max-width: 640px) {{
                .history-table-wrap {{
                    width: 100% !important;
                    max-width: 100% !important;
                    min-width: 100% !important;
                    overflow-x: visible !important;
                    box-sizing: border-box !important;
                }}
                
                .history-table {{
                    min-width: 100% !important;
                    width: 100% !important;
                    max-width: 100% !important;
                    box-sizing: border-box !important;
                }}
                
                /* Hide checking, savings, retirement columns on mobile */
                .history-table th:nth-child(2),
                .history-table th:nth-child(3),
                .history-table th:nth-child(4),
                .history-table td:nth-child(2),
                .history-table td:nth-child(3),
                .history-table td:nth-child(4) {{
                    display: none;
                }}
                
                /* Make remaining columns larger and spread across full width */
                .history-table th,
                .history-table td {{
                    padding: 16px 16px;
                    font-size: 14px;
                }}
                
                /* Date column takes up more space */
                .history-table th:first-child,
                .history-table td:first-child {{
                    width: 35%;
                }}
                
                /* Net worth column takes up remaining space */
                .history-table th:nth-child(5),
                .history-table td:nth-child(5) {{
                    width: 50%;
                    text-align: right;
                    font-size: 16px;
                    font-weight: 600;
                }}
                
                /* Delete button column */
                .history-table th:nth-child(6),
                .history-table td:nth-child(6) {{
                    width: 15%;
                    text-align: center;
                }}
                
                /* For forecast table (only 2 columns), override the hide rule for 2nd column */
                .history-table th:nth-child(2):last-child,
                .history-table td:nth-child(2):last-child {{
                    display: table-cell !important; /* Show 2nd column if it's the last one */
                    text-align: right;
                    font-size: 16px;
                    font-weight: 600;
                    width: 50%;
                }}
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">M</div>
                <div class="logo-text">Mukunda</div>
            </div>
            <nav>
                <a href="/" class="{balances_active}">Balances</a>
                <a href="/history" class="{history_active}">History</a>
                <a href="/forecast" class="{forecast_active}">Forecast</a>
            </nav>
        </header>
"""


def get_html_footer():
    """Generate closing HTML and JavaScript for the page."""
    
    return """
    </div>
    <script>
        // Bills toggle functionality - shows/hides bill details when clicked
        document.querySelectorAll('.bills-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('open');
                const content = btn.nextElementSibling;
                content.classList.toggle('show');
            });
        });
        
        // Format inputs on blur - ensures numbers have 2 decimal places
        document.querySelectorAll('.account-input:not([readonly])').forEach(input => {
            input.addEventListener('blur', function() {
                // Remove any non-number characters and parse as float
                let val = parseFloat(this.value.replace(/[^0-9.-]/g, '')) || 0;
                // Format with 2 decimal places
                this.value = val.toFixed(2);
            });
        });
    </script>
</body>
</html>"""


def account_row(account_name, balances, readonly=False):
    """Generate HTML for a single account input row.
    readonly=True means the user can't edit it (like Bills total).
    For credit cards and bills, display absolute value (user enters positive, we store negative)."""
    
    readonly_attr = "readonly" if readonly else ""
    
    # Get the stored value
    stored_value = balances.get(account_name, 0)
    
    # For credit cards and bills, show absolute value in the input field
    # (stored as -1500, display as 1500)
    if account_name in CREDIT_CARDS or account_name in BILLS:
        display_value = abs(stored_value)
        # Only add the minus sign visual indicator for credit cards and Bills total
        # Not for individual bill items (they're obviously bills)
        card_class = "credit-card" if account_name in CREDIT_CARDS else ""
    else:
        display_value = stored_value
        card_class = ""
    
    return f'''
        <div class="account-row {card_class}">
            <span class="account-name">{clean_name(account_name)}</span>
            <input type="text" inputmode="decimal" class="account-input" 
                   name="{account_name}" value="{display_value:.2f}" {readonly_attr}>
        </div>'''


# SVG icons for the cards (defined as a dictionary for easy access)
ICONS = {
    "credit": '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 10h18M7 15h.01M11 15h2"/><rect x="3" y="6" width="18" height="12" rx="2"/></svg>',
    "savings": '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>',
    "retirement": '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>',
    "chevron": '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>'
}


# ============================================================================
# ROUTES (URL HANDLERS)
# ============================================================================

@app.route("/", methods=["GET", "POST"])
def home():
    """Main dashboard page.
    GET: Display the form with current balances
    POST: Save updated balances and create history snapshot"""
    
    balances = load()
    
    # If user submitted the form (clicked Save)
    if request.method == "POST":
        # Loop through all accounts and update their values from the form
        for account_name in balances:
            if account_name == "Bills":
                continue  # Skip Bills - it's auto-calculated
            
            value = request.form.get(account_name)
            if value:
                # Clean up the input (remove commas and $ signs) and convert to float
                amount = float(value.replace(",", "").replace("$", "") or 0)
                
                # For credit cards and individual bills, convert positive amounts to negative (credits)
                # User enters 1500, we store -1500 (because it's money you owe)
                if account_name in CREDIT_CARDS or account_name in BILLS:
                    amount = -abs(amount)  # Force negative
                
                balances[account_name] = amount
        
        # Auto-calculate Bills as sum of all bill accounts (stored as negative)
        # User enters positive amounts for each bill, we sum absolute values and make negative
        bills_total = sum(abs(balances[bill_name]) for bill_name in BILLS)
        balances["Bills"] = -bills_total
        
        # Save to file and create history snapshot
        save(balances)
        save_snapshot(balances)
    
    # Calculate category totals
    total_checking = tot(CHECKS + ["Bills"], balances)
    total_savings = tot(SAVES, balances)
    total_retirement = tot(RETIRE, balances)
    net_worth = total_checking + total_savings + total_retirement
    
    # Build HTML for each account section
    checking_rows = "".join(account_row(name, balances) for name in CHECKS)
    bills_rows = "".join(account_row(name, balances) for name in BILLS)
    savings_rows = "".join(account_row(name, balances) for name in SAVES)
    retirement_rows = "".join(account_row(name, balances) for name in RETIRE)
    
    # Return complete HTML page
    return get_html_header("Balances", "balances") + f"""
        <div class="hero">
            <div class="hero-label">Total Net Worth</div>
            <div class="hero-value">{fmt(net_worth)}</div>
        </div>
        
        <form method="POST">
            <div class="grid">
                <!-- Checking & Credit Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon green">{ICONS['credit']}</div>
                            <span class="card-label">Checking & Credit</span>
                        </div>
                        <div class="card-total">{fmt(total_checking)}</div>
                    </div>
                    <div class="account-list">
                        {checking_rows}
                        {account_row("Bills", balances, readonly=True)}
                        <button type="button" class="bills-toggle">
                            <span>View Bills Breakdown</span>
                            {ICONS['chevron']}
                        </button>
                        <div class="bills-content">
                            {bills_rows}
                        </div>
                    </div>
                </div>
                
                <!-- Savings & Assets Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon purple">{ICONS['savings']}</div>
                            <span class="card-label">Savings & Assets</span>
                        </div>
                        <div class="card-total">{fmt(total_savings)}</div>
                    </div>
                    <div class="account-list">
                        {savings_rows}
                    </div>
                </div>
                
                <!-- Retirement Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon orange">{ICONS['retirement']}</div>
                            <span class="card-label">Retirement</span>
                        </div>
                        <div class="card-total">{fmt(total_retirement)}</div>
                    </div>
                    <div class="account-list">
                        {retirement_rows}
                    </div>
                </div>
            </div>
            
            <div class="save-section">
                <button type="submit" class="save-btn">Save All Changes</button>
            </div>
        </form>
""" + get_html_footer()


def get_chart_data(snapshots):
    """Convert history snapshots into chart-ready data.
    Returns two lists: dates and net worth values."""
    
    dates = []
    net_worths = []
    
    # Process each snapshot in order (oldest to newest)
    for snapshot in snapshots:
        # Extract date from timestamp (format: "YYYY-MM-DD HH:MM:SS")
        timestamp = snapshot.get("timestamp", "")
        date_parts = timestamp.split(" ")[0].split("-")
        
        # Format date as MM/DD for display
        if len(date_parts) == 3:
            date_formatted = f"{date_parts[1]}/{date_parts[2]}"
        else:
            date_formatted = timestamp
        
        dates.append(date_formatted)
        
        # Calculate net worth for this snapshot
        checking = tot(CHECKS + ["Bills"], snapshot)
        savings = tot(SAVES, snapshot)
        retirement = tot(RETIRE, snapshot)
        net_worth = checking + savings + retirement
        
        net_worths.append(net_worth)
    
    return dates, net_worths


@app.route("/history", methods=["GET", "POST"])
def history():
    """History page showing chart and table of past snapshots.
    POST: Handle deleting a snapshot"""
    
    # Handle delete button click
    if request.method == "POST":
        index_to_delete = request.form.get("delete_index")
        if index_to_delete:
            snapshots = load_history()
            try:
                index = int(index_to_delete)
                # Check index is valid, then remove that snapshot
                if 0 <= index < len(snapshots):
                    snapshots.pop(index)
                    json.dump(snapshots, open(HISTORY_FILE, 'w'), indent=4)
            except (ValueError, IndexError):
                pass  # Invalid index, just ignore
    
    snapshots = load_history()
    # Reverse so newest appears first in table
    snapshots_reversed = list(reversed(snapshots))
    
    # Show empty state if no history yet
    if not snapshots_reversed:
        return get_html_header("History", "history") + """
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <p class="empty-text">No history yet. Save your first snapshot from the dashboard to start tracking your wealth over time.</p>
            </div>
""" + get_html_footer()
    
    # Get chart data (use original order for chronological chart)
    dates, net_worths = get_chart_data(snapshots)
    
    # Convert to JSON strings for JavaScript
    dates_json = json.dumps(dates)
    net_worths_json = json.dumps(net_worths)
    
    # Build table rows (newest first)
    table_rows = ""
    for idx, snapshot in enumerate(snapshots_reversed):
        # Format date for table display
        timestamp = snapshot.get("timestamp", "Unknown")
        date_parts = timestamp.split(" ")[0].split("-")
        if len(date_parts) == 3:
            date_formatted = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
        else:
            date_formatted = timestamp
        
        # Calculate totals for this snapshot
        snap_checks = tot(CHECKS + ["Bills"], snapshot)
        snap_saves = tot(SAVES, snapshot)
        snap_retire = tot(RETIRE, snapshot)
        snap_total = snap_checks + snap_saves + snap_retire
        
        # Get original index for deletion (since we reversed the list)
        original_index = len(snapshots) - 1 - idx
        
        # Build table row HTML
        table_rows += f'''
            <tr>
                <td class="history-date">{date_formatted}</td>
                <td>{fmt(snap_checks)}</td>
                <td>{fmt(snap_saves)}</td>
                <td>{fmt(snap_retire)}</td>
                <td class="history-total">{fmt(snap_total)}</td>
                <td style="text-align: center; padding: 8px;">
                    <form method="POST" style="display: inline;">
                        <button type="submit" name="delete_index" value="{original_index}" class="delete-btn">×</button>
                    </form>
                </td>
            </tr>'''
    
    # Get most recent snapshot for pie chart
    latest_snapshot = snapshots[-1]  # Last item is most recent
    latest_checking = tot(CHECKS + ["Bills"], latest_snapshot)
    latest_savings = tot(SAVES, latest_snapshot)
    latest_retirement = tot(RETIRE, latest_snapshot)
    
    # Return complete history page with charts and table
    return get_html_header("History", "history") + f"""
        <div class="history-header">
            <h1 class="history-title">Balance History</h1>
            <p class="history-subtitle">Track your financial journey over time</p>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <canvas id="netWorthChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="breakdownChart"></canvas>
            </div>
        </div>
        
        <div class="history-table-wrap">
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Checking/Credit</th>
                        <th>Savings/Assets</th>
                        <th>Retirement</th>
                        <th>Net Worth</th>
                        <th style="width: 60px;"></th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        <script>
            // Get data from Python backend
            const dates = {dates_json};
            const netWorths = {net_worths_json};
            
            // Create line chart using Chart.js library
            const ctx = document.getElementById('netWorthChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: dates,
                    datasets: [{{
                        label: 'Net Worth',
                        data: netWorths,
                        borderColor: '#00d4aa',
                        backgroundColor: 'rgba(0, 212, 170, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 5,
                        pointBackgroundColor: '#00d4aa',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 7
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            labels: {{
                                color: 'rgba(255, 255, 255, 0.6)',
                                font: {{ family: "'DM Sans', sans-serif", size: 14 }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            grid: {{
                                color: 'rgba(255, 255, 255, 0.08)',
                                drawBorder: false
                            }},
                            ticks: {{
                                color: 'rgba(255, 255, 255, 0.6)',
                                callback: function(value) {{
                                    return '$' + value.toLocaleString();
                                }}
                            }}
                        }},
                        x: {{
                            grid: {{
                                display: false,
                                drawBorder: false
                            }},
                            ticks: {{
                                color: 'rgba(255, 255, 255, 0.6)'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Create pie chart showing breakdown of most recent snapshot
            const pieCtx = document.getElementById('breakdownChart').getContext('2d');
            new Chart(pieCtx, {{
                type: 'doughnut',
                data: {{
                    labels: ['Checking/Credit', 'Savings/Assets', 'Retirement'],
                    datasets: [{{
                        data: [{latest_checking}, {latest_savings}, {latest_retirement}],
                        backgroundColor: [
                            'rgba(0, 212, 170, 0.8)',
                            'rgba(168, 85, 247, 0.8)',
                            'rgba(249, 115, 22, 0.8)'
                        ],
                        borderColor: [
                            '#00d4aa',
                            '#a855f7',
                            '#f97316'
                        ],
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'bottom',
                            labels: {{
                                color: 'rgba(255, 255, 255, 0.6)',
                                font: {{ family: "'DM Sans', sans-serif", size: 12 }},
                                padding: 15
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        </script>
""" + get_html_footer()


# ============================================================================
# START THE SERVER
# ============================================================================

@app.route("/forecast")
def forecast():
    """Forecast page showing projected savings and retirement growth.
    User can input monthly contribution amount to see 12-month projection."""
    
    balances = load()
    
    # Get current totals for savings and retirement
    current_savings = tot(SAVES, balances)
    current_retirement = tot(RETIRE, balances)
    
    # Get monthly contribution from URL parameter, or load from saved settings
    if request.args.get('contribution') is not None:
        # User submitted the form - use their input and save it
        monthly_contribution = float(request.args.get('contribution', 0))
        save_forecast_settings(monthly_contribution)
    else:
        # Load previously saved contribution amount
        monthly_contribution = load_forecast_settings()
    
    # Generate 12 months of forecasts starting from current month
    import calendar
    from datetime import datetime
    
    current_date = datetime.now()
    
    # Build forecast data for each of the next 12 months
    forecast_months = []
    forecast_savings = []
    forecast_retirement = []
    forecast_combined = []
    
    for month_offset in range(12):
        # Calculate which month we're forecasting
        month_num = (current_date.month + month_offset - 1) % 12 + 1
        year_offset = (current_date.month + month_offset - 1) // 12
        year = current_date.year + year_offset
        
        # Get month name (Jan, Feb, etc)
        month_name = calendar.month_abbr[month_num]
        forecast_months.append(f"{month_name} {year}")
        
        # Calculate projected combined amount
        # Starting total + (monthly contribution × number of months)
        # NOTE: We add to the COMBINED total, not separately to savings and retirement
        # This prevents double-counting the contribution
        starting_combined = current_savings + current_retirement
        projected_combined = starting_combined + (monthly_contribution * month_offset)
        
        forecast_combined.append(projected_combined)
    
    # Convert to JSON for JavaScript
    months_json = json.dumps(forecast_months)
    combined_json = json.dumps(forecast_combined)
    
    # Calculate end-of-year totals
    end_combined = forecast_combined[-1]
    total_contributed = monthly_contribution * 12
    
    return get_html_header("Forecast", "forecast") + f"""
        <div class="history-header">
            <h1 class="history-title">12-Month Forecast</h1>
            <p class="history-subtitle">Project your savings and retirement growth</p>
        </div>
        
        <!-- Chart -->
        <div class="charts-grid" style="grid-template-columns: 1fr;">
            <div class="chart-container">
                <canvas id="forecastChart"></canvas>
            </div>
        </div>
        
        <!-- Input Box and Table Grid -->
        <div class="forecast-content-grid">
            <!-- Input Section -->
            <div class="forecast-input-card">
                <div class="forecast-input-header">
                    <h3 class="forecast-input-title">Monthly Contribution</h3>
                    <p class="forecast-input-subtitle">How much will you add each month?</p>
                </div>
                
                <form method="GET" action="/forecast" class="forecast-form">
                    <div class="forecast-input-group">
                        <span class="forecast-dollar">$</span>
                        <input type="text" inputmode="decimal" name="contribution" value="{monthly_contribution:.2f}" 
                               class="forecast-input" placeholder="0.00" autofocus>
                    </div>
                    <button type="submit" class="forecast-btn">Update Forecast</button>
                </form>
                
                <div class="forecast-stats-vertical">
                    <div class="forecast-stat-vertical">
                        <div class="forecast-stat-label">Starting Total</div>
                        <div class="forecast-stat-value">{fmt(current_savings + current_retirement)}</div>
                    </div>
                    <div class="forecast-stat-vertical">
                        <div class="forecast-stat-label">Total Added (12 months)</div>
                        <div class="forecast-stat-value">{fmt(total_contributed)}</div>
                    </div>
                    <div class="forecast-stat-vertical">
                        <div class="forecast-stat-label">Projected End Total</div>
                        <div class="forecast-stat-value forecast-stat-highlight">{fmt(end_combined)}</div>
                    </div>
                </div>
            </div>
            
            <!-- Forecast Table -->
            <div class="history-table-wrap">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Month</th>
                            <th>Projected Total</th>
                        </tr>
                    </thead>
                    <tbody id="forecastTableBody">
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            // Get forecast data from Python
            const months = {months_json};
            const combinedData = {combined_json};
            
            // Create forecast chart with only combined total line
            const ctx = document.getElementById('forecastChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: months,
                    datasets: [
                        {{
                            label: 'Savings + Retirement Total',
                            data: combinedData,
                            borderColor: '#00d4aa',
                            backgroundColor: 'rgba(0, 212, 170, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 5,
                            pointBackgroundColor: '#00d4aa',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointHoverRadius: 7
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            labels: {{
                                color: 'rgba(255, 255, 255, 0.6)',
                                font: {{ family: "'DM Sans', sans-serif", size: 14 }},
                                padding: 15
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': $' + context.parsed.y.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            grid: {{
                                color: 'rgba(255, 255, 255, 0.08)',
                                drawBorder: false
                            }},
                            ticks: {{
                                color: 'rgba(255, 255, 255, 0.6)',
                                callback: function(value) {{
                                    return '$' + value.toLocaleString();
                                }}
                            }}
                        }},
                        x: {{
                            grid: {{
                                display: false,
                                drawBorder: false
                            }},
                            ticks: {{
                                color: 'rgba(255, 255, 255, 0.6)'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Build forecast table rows (simplified - only month and total)
            const tableBody = document.getElementById('forecastTableBody');
            for (let i = 0; i < months.length; i++) {{
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="history-date">${{months[i]}}</td>
                    <td class="history-total">$${{combinedData[i].toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</td>
                `;
                tableBody.appendChild(row);
            }}
            
            // Format forecast input on blur (same as dashboard behavior)
            const forecastInput = document.querySelector('.forecast-input');
            if (forecastInput) {{
                forecastInput.addEventListener('blur', function() {{
                    // Remove any non-number characters and parse as float
                    let val = parseFloat(this.value.replace(/[^0-9.-]/g, '')) || 0;
                    // Format with 2 decimal places
                    this.value = val.toFixed(2);
                }});
            }}
        </script>
        
        <style>
            .forecast-content-grid {{
                display: grid;
                grid-template-columns: 400px 1fr;
                gap: 24px;
                align-items: start;
            }}
            
            @media (max-width: 968px) {{
                .forecast-content-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            .forecast-input-card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 24px;
                padding: 32px;
                backdrop-filter: blur(20px);
                animation: fadeUp 0.6s ease-out;
                position: sticky;
                top: 20px;
            }}
            
            .forecast-input-header {{
                margin-bottom: 24px;
            }}
            
            .forecast-input-title {{
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 4px;
            }}
            
            .forecast-input-subtitle {{
                font-size: 14px;
                color: var(--text-muted);
            }}
            
            .forecast-form {{
                margin-bottom: 28px;
            }}
            
            .forecast-input-group {{
                display: flex;
                align-items: center;
                gap: 12px;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 12px 20px;
                transition: all 0.3s ease;
                margin-bottom: 12px;
            }}
            
            .forecast-input-group:focus-within {{
                border-color: var(--accent);
                background: rgba(0, 212, 170, 0.05);
                box-shadow: 0 0 0 4px var(--accent-soft);
            }}
            
            .forecast-dollar {{
                font-size: 24px;
                font-weight: 600;
                color: var(--text-secondary);
            }}
            
            .forecast-input {{
                flex: 1;
                background: none;
                border: none;
                color: var(--text-primary);
                font-size: 24px;
                font-family: 'DM Sans', sans-serif;
                font-weight: 600;
                outline: none;
                min-width: 0;
            }}
            
            .forecast-input::placeholder {{
                color: var(--text-muted);
            }}
            
            .forecast-btn {{
                width: 100%;
                padding: 16px 28px;
                background: linear-gradient(135deg, var(--accent), #00a080);
                border: none;
                border-radius: 12px;
                color: var(--bg-dark);
                font-size: 14px;
                font-weight: 700;
                font-family: 'DM Sans', sans-serif;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .forecast-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px var(--accent-glow);
            }}
            
            .forecast-stats-vertical {{
                display: flex;
                flex-direction: column;
                gap: 20px;
                padding-top: 28px;
                border-top: 1px solid var(--border);
            }}
            
            .forecast-stat-vertical {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .forecast-stat-label {{
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: var(--text-muted);
            }}
            
            .forecast-stat-value {{
                font-family: 'Instrument Serif', serif;
                font-size: 20px;
                color: var(--text-primary);
            }}
            
            .forecast-stat-highlight {{
                color: var(--accent);
            }}
        </style>
""" + get_html_footer()


if __name__ == "__main__":
    # Run Flask development server
    # debug=True: Shows helpful error messages and auto-reloads on code changes
    # port=5001: The web address will be http://localhost:5001
    # use_reloader=False: Prevents running the app twice in debug mode
    app.run(debug=True, port=5001, use_reloader=False)
