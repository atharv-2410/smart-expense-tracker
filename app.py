"""Smart Expense Tracker & Budget Analyzer - run with:  streamlit run app.py"""
import calendar
import io
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as an
import db
import importer as imp
import ml
import seed

st.set_page_config(
    page_title="Smart Expense Tracker | Your Money, in Focus",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)
db.init_db()

# ---------------------------------------------------------------- Design Tokens & Color Palette
CATEGORY_COLORS = {
    "Rent": "#2563eb",             # Royal Blue - visually dominant for primary fixed cost
    "Food": "#f59e0b",             # Amber
    "Groceries": "#10b981",        # Emerald
    "Travel": "#8b5cf6",           # Purple
    "Shopping": "#ec4899",         # Pink
    "Entertainment": "#6366f1",    # Indigo
    "Bills & Utilities": "#06b6d4",# Cyan
    "Health": "#ef4444",           # Rose/Red
    "Education": "#14b8a6",        # Teal
    "Other": "#64748b",            # Slate
    "Income": "#059669",           # Forest Green
}

STATUS_COLORS = {
    "ok": "#10b981",
    "warning": "#f59e0b",
    "over": "#ef4444",
}

LEVEL_ICON = {"danger": "🚨", "warn": "⚠️", "info": "ℹ️", "good": "✅"}


def inr(x):
    return f"₹{x:,.0f}"


# ---------------------------------------------------------------- Global CSS & Design System
CUSTOM_CSS = """
<style>
/* Import Google Fonts: Newsreader (Editorial Serif) & Inter (Modern UI Sans) */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1e293b;
}

/* Page Layout */
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1240px !important;
}

/* Typography Scale */
.page-header-container {
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f1f5f9;
}

.page-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b; /* WCAG AA compliant on light background */
    margin-bottom: 6px;
}

.page-title {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 2.35rem;
    font-weight: 600;
    color: #0f172a;
    letter-spacing: -0.015em;
    line-height: 1.15;
    margin: 0 0 6px 0;
}

.page-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    color: #475569;
    margin: 0;
    line-height: 1.5;
}

/* KPI Card Hierarchy */
.kpi-grid {
    display: grid;
    gap: 16px;
    margin-bottom: 24px;
}

.kpi-card {
    border-radius: 12px;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 128px;
    box-sizing: border-box;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
}

.kpi-hero {
    background: linear-gradient(145deg, #0f172a 0%, #134e4a 100%);
    border: 1px solid #0d9488;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.16);
}

.kpi-secondary {
    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
}

.kpi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}

.kpi-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.hero-eyebrow {
    color: #5eead4;
}

.secondary-eyebrow {
    color: #94a3b8;
}

.kpi-value {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 2.15rem;
    font-weight: 600;
    line-height: 1.1;
    letter-spacing: -0.02em;
    margin: 4px 0 8px 0;
}

.hero-value {
    color: #ffffff;
}

.secondary-value {
    color: #f8fafc;
}

.kpi-subtext {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    line-height: 1.4;
}

.hero-subtext {
    color: #94a3b8;
}

.secondary-subtext {
    color: #94a3b8;
}

.kpi-badge {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 9999px;
    letter-spacing: 0.04em;
    display: inline-block;
}

.kpi-badge.hero {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
}

.kpi-badge.good {
    background: #d1fae5;
    color: #065f46;
}

.kpi-badge.warn {
    background: #fef3c7;
    color: #92400e;
}

.kpi-badge.danger {
    background: #fee2e2;
    color: #991b1b;
}

/* Alert Notification Banners */
.alert-banner {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 0.88rem;
    line-height: 1.45;
}

.alert-banner.danger {
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
}

.alert-banner.warn {
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    color: #92400e;
}

.alert-banner.good {
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #166534;
}

.alert-banner.info {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1e40af;
}

/* Section Card Container */
.section-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 22px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.section-heading {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 1.35rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0 0 14px 0;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #f8fafc !important;
    border-right: 1px solid #e2e8f0 !important;
}

.sidebar-brand-box {
    padding: 14px 16px;
    border-radius: 10px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    margin-bottom: 20px;
}

.sidebar-brand-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #059669;
    margin-bottom: 2px;
}

.sidebar-brand-title {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0;
    line-height: 1.2;
}

.sidebar-user-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    font-size: 0.82rem;
    color: #475569;
    font-weight: 500;
}

.sidebar-user-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10b981;
}

/* Navigation items: Consistent Feather / Lucide SVGs, active green dot + border, and hover state */
div[data-testid="stRadio"] div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    color: #475569 !important;
    font-weight: 500 !important;
    border-left: 3px solid transparent !important;
    background-color: transparent !important;
}

/* Hide native radio circle bullet */
div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

div[data-testid="stRadio"] div[role="radiogroup"] > label > div:last-child {
    font-size: 0.88rem !important;
    font-family: 'Inter', sans-serif !important;
    color: inherit !important;
    letter-spacing: -0.01em !important;
}

/* Hover state across all items */
div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
}

/* Active item state: Emerald border + light emerald background */
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
    background-color: #f0fdf4 !important;
    color: #065f46 !important;
    font-weight: 600 !important;
    border-left: 3px solid #10b981 !important;
}

/* Active item green dot on the right side */
div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked)::after {
    content: '' !important;
    display: block !important;
    width: 6px !important;
    height: 6px !important;
    background-color: #10b981 !important;
    border-radius: 50% !important;
    margin-left: auto !important;
    box-shadow: 0 0 0 2px #d1fae5 !important;
}

/* Icon baseline styling */
div[data-testid="stRadio"] div[role="radiogroup"] > label::before {
    content: '' !important;
    display: inline-block !important;
    width: 17px !important;
    height: 17px !important;
    margin-right: 11px !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    flex-shrink: 0 !important;
}

/* 1. Dashboard: Grid / Layout icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(1)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(1):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>') !important;
}

/* 2. Add Transaction: Plus Circle icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(2)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(2):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>') !important;
}

/* 3. Transactions: List / Receipt icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(3)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-8"/><path d="M16 12h-8"/><path d="M14 16h-6"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(3):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-8"/><path d="M16 12h-8"/><path d="M14 16h-6"/></svg>') !important;
}

/* 4. Budgets: Target icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(4)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(4):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>') !important;
}

/* 5. Insights & Forecast: Trending Up icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(5)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(5):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>') !important;
}

/* 6. People Ledger: Users icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(6)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(6):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>') !important;
}

/* 7. Import / Export: Arrow Down Up icon */
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(7)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 16 4 4 4-4"/><path d="M7 20V4"/><path d="m21 8-4-4-4 4"/><path d="M17 4v16"/></svg>') !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(7):has(input:checked)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%23059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 16 4 4 4-4"/><path d="M7 20V4"/><path d="m21 8-4-4-4 4"/><path d="M17 4v16"/></svg>') !important;
}

/* ================================================================
   Auth Page: Card Treatment, Form Inputs, Tabs, Button Contrast & Validation
   ================================================================ */
/* Center Auth Card Container */
.auth-container {
    max-width: 460px;
    margin: 24px auto 48px auto;
}

.auth-card {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    border-top: 4px solid #0d9488; /* Teal brand accent top border */
    box-shadow: 0 12px 28px -6px rgba(13, 148, 136, 0.1), 0 8px 12px -6px rgba(0, 0, 0, 0.04);
    overflow: hidden;
}

.auth-hero-banner {
    background: linear-gradient(145deg, #0f172a 0%, #134e4a 100%);
    padding: 28px 28px 22px 28px;
    color: #ffffff;
    position: relative;
    border-bottom: 1px solid #1e293b;
}

.auth-hero-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5eead4; /* Mint/teal accent */
    margin-bottom: 6px;
}

.auth-hero-title {
    font-family: 'Newsreader', Georgia, serif;
    font-size: 2.1rem;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.015em;
    line-height: 1.15;
    margin: 0 0 6px 0;
}

.auth-hero-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.45;
    margin: 0;
}

.auth-body {
    padding: 24px 28px 30px 28px;
}

/* Tabs: Active teal highlight underline & clean muted hierarchy */
div[data-baseweb="tab-highlight"] {
    background-color: #0d9488 !important; /* Teal brand accent matching dashboard */
    height: 3px !important;
    border-radius: 3px 3px 0 0 !important;
}

div[data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: 1px solid #e2e8f0 !important;
    margin-bottom: 22px !important;
    padding-bottom: 2px !important;
}

/* Inactive tabs: visually muted lighter text weight & slate color */
button[data-baseweb="tab"] {
    color: #64748b !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    padding: 8px 16px !important;
    border-radius: 6px 6px 0 0 !important;
    transition: color 0.15s ease, background-color 0.15s ease !important;
    background: transparent !important;
    border: none !important;
}

button[data-baseweb="tab"]:hover {
    color: #0f172a !important;
    background-color: #f8fafc !important;
}

/* Active tab: Clear hierarchy with deep teal text and semibold weight */
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0f766e !important;
    font-weight: 600 !important;
}

/* Input labels: Eyebrow uppercase tracked style matching dashboard */
label[data-testid="stWidgetLabel"] {
    margin-bottom: 6px !important;
}

label[data-testid="stWidgetLabel"] p {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #475569 !important; /* High-contrast slate */
}

/* Input container: rounded border, clean padding, and teal focus state */
div[data-baseweb="input"] {
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    background-color: #ffffff !important;
    border-radius: 8px !important;
    border: 1px solid #cbd5e1 !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    min-height: 42px !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #0d9488 !important; /* Teal focus highlight */
    box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.16) !important;
}

div[data-baseweb="input"] input {
    background-color: transparent !important;
    color: #0f172a !important;
    padding: 10px 42px 10px 14px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Password visibility toggle button fix:
   Replaces broken dark rectangular button with vertically-centered icon button,
   no overlap/clipping, transparent background, and smooth hover state. */
div[data-baseweb="input"] button,
div[data-baseweb="input"] > div:last-child button,
button[data-testid="stTextInputPasswordVisibilityButton"] {
    position: absolute !important;
    right: 8px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 4px !important;
    margin: 0 !important;
    min-height: unset !important;
    min-width: unset !important;
    width: 30px !important;
    height: 30px !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 6px !important;
    color: #64748b !important;
    transition: color 0.15s ease, background-color 0.15s ease !important;
    z-index: 5 !important;
}

div[data-baseweb="input"] button:hover,
button[data-testid="stTextInputPasswordVisibilityButton"]:hover {
    color: #0f172a !important;
    background-color: #f1f5f9 !important;
}

div[data-baseweb="input"] button svg,
button[data-testid="stTextInputPasswordVisibilityButton"] svg {
    width: 17px !important;
    height: 17px !important;
    fill: none !important;
    stroke: currentColor !important;
    stroke-width: 2 !important;
}

/* Hide raw text string like 'visibility' if font ligature fails */
div[data-baseweb="input"] button span {
    font-size: 0 !important;
    color: transparent !important;
}

/* Primary Form Submit Button (Login, Register) & Auth Buttons:
   Teal/green gradient background with crisp white text, meeting WCAG AA contrast (> 4.8:1) */
div[data-testid="stFormSubmitButton"] > button,
button[kind="primaryFormSubmit"],
.auth-submit-btn,
.auth-card .stButton > button {
    background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
    color: #ffffff !important;
    border: 1px solid #0f766e !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    padding: 10px 24px !important;
    width: 100% !important;
    box-shadow: 0 2px 6px rgba(13, 148, 136, 0.25) !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
    margin-top: 10px !important;
}

div[data-testid="stFormSubmitButton"] > button:hover,
.auth-card .stButton > button:hover {
    background: linear-gradient(135deg, #0f766e 0%, #115e59 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(13, 148, 136, 0.35) !important;
    transform: translateY(-1px) !important;
}

div[data-testid="stFormSubmitButton"] > button:active,
.auth-card .stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 3px rgba(13, 148, 136, 0.2) !important;
}

div[data-testid="stFormSubmitButton"] > button p,
div[data-testid="stFormSubmitButton"] > button span,
.auth-card .stButton > button p,
.auth-card .stButton > button span {
    color: #ffffff !important;
    font-weight: 600 !important;
}

/* Alert Notification Overrides for Auth Validation */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    padding: 11px 15px !important;
    margin-top: 14px !important;
    margin-bottom: 14px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    line-height: 1.45 !important;
}

div[data-testid="stAlert"]:has([data-testid="stAlertErrorIcon"]),
div[data-testid="stAlert"][data-baseweb="notification"][kind="negative"] {
    background-color: #fef2f2 !important;
    border: 1px solid #fecaca !important;
    color: #991b1b !important;
}

div[data-testid="stAlert"]:has([data-testid="stAlertWarningIcon"]),
div[data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {
    background-color: #fffbeb !important;
    border: 1px solid #fde68a !important;
    color: #92400e !important;
}

div[data-testid="stAlert"] p {
    color: inherit !important;
    font-weight: 500 !important;
    margin: 0 !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- UI Helper Components
def render_header(eyebrow: str, title: str, subtitle: str = ""):
    sub_html = f'<p class="page-subtitle">{subtitle}</p>' if subtitle else ''
    html = (
        f'<div class="page-header-container">'
        f'<div class="page-eyebrow">{eyebrow}</div>'
        f'<h1 class="page-title">{title}</h1>'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_kpis(hero: dict, secondaries: list[dict]):
    """
    Renders the consistent KPI card hierarchy:
    - hero: Dark hero card for primary volume/spend/projection
    - secondaries: Styled dark cards for supporting metrics
    """
    hero_badge_html = f'<span class="kpi-badge hero">{hero["badge"]}</span>' if hero.get("badge") else ""
    hero_html = (
        f'<div class="kpi-card kpi-hero">'
        f'<div class="kpi-header">'
        f'<span class="kpi-eyebrow hero-eyebrow">{hero["eyebrow"]}</span>'
        f'{hero_badge_html}'
        f'</div>'
        f'<div class="kpi-value hero-value">{hero["value"]}</div>'
        f'<div class="kpi-subtext hero-subtext">{hero.get("subtext", "")}</div>'
        f'</div>'
    )

    sec_cards = []
    for s in secondaries:
        badge_cls = s.get("badge_type", "good")
        badge_html = f'<span class="kpi-badge {badge_cls}">{s["badge"]}</span>' if s.get("badge") else ""
        card = (
            f'<div class="kpi-card kpi-secondary">'
            f'<div class="kpi-header">'
            f'<span class="kpi-eyebrow secondary-eyebrow">{s["eyebrow"]}</span>'
            f'{badge_html}'
            f'</div>'
            f'<div class="kpi-value secondary-value">{s["value"]}</div>'
            f'<div class="kpi-subtext secondary-subtext">{s.get("subtext", "")}</div>'
            f'</div>'
        )
        sec_cards.append(card)

    total_cols = 1 + len(secondaries)
    grid_css = f"grid-template-columns: repeat({total_cols}, minmax(0, 1fr));"
    cards_html = "".join([hero_html] + sec_cards)
    html = f'<div class="kpi-grid" style="{grid_css}">{cards_html}</div>'
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------- Authentication
def auth_screen():
    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-hero-banner">
                    <div class="auth-hero-eyebrow">PERSONAL FINANCE INTELLIGENCE</div>
                    <div class="auth-hero-title">Your money, in focus</div>
                    <p class="auth-hero-subtitle">
                        Auto-categorise personal spending, forecast month-end totals early, and uncover actionable financial insights.
                    </p>
                </div>
                <div class="auth-body">
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_reg, tab_demo = st.tabs(["Login", "Register", "Try demo"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email", placeholder="name@example.com")
            pw = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_login = st.form_submit_button("Sign In")
            if submit_login:
                if not email.strip() or not pw.strip():
                    st.error("Please enter both your email and password.")
                else:
                    u = db.login(email, pw)
                    if u:
                        st.session_state.user = u
                        st.rerun()
                    else:
                        st.error("Invalid email or password. Please verify your credentials.")

    with tab_reg:
        with st.form("register"):
            name = st.text_input("Full Name", placeholder="Your name")
            email = st.text_input("Email Address", key="reg_email", placeholder="name@example.com")
            pw = st.text_input("Password", type="password", key="reg_pw", placeholder="Minimum 4 characters")
            submit_reg = st.form_submit_button("Create Free Account")
            if submit_reg:
                if not name.strip() or not email.strip():
                    st.error("Please provide both your name and email address.")
                elif len(pw) < 4:
                    st.error("Password must contain at least 4 characters.")
                else:
                    uid, err = db.register(name, email, pw)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.user = db.login(email, pw)
                        st.rerun()

    with tab_demo:
        st.markdown(
            """
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin-bottom: 16px;">
                <div style="font-weight: 600; color: #0f172a; margin-bottom: 6px; font-size: 0.95rem;">
                    Instant Sandbox Access
                </div>
                <p style="color: #475569; font-size: 0.86rem; line-height: 1.5; margin-bottom: 14px;">
                    Loads a prepared account pre-populated with 3 months of realistic multi-category spending,
                    stipend credits, hostel rent, and deliberate statistical outliers for anomaly detection.
                </p>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <span style="background: #f0fdf4; color: #166534; font-size: 0.72rem; font-weight: 600; padding: 4px 10px; border-radius: 9999px; border: 1px solid #bbf7d0;">3 Months Ledger</span>
                    <span style="background: #f0fdf4; color: #166534; font-size: 0.72rem; font-weight: 600; padding: 4px 10px; border-radius: 9999px; border: 1px solid #bbf7d0;">Pre-trained ML</span>
                    <span style="background: #f0fdf4; color: #166534; font-size: 0.72rem; font-weight: 600; padding: 4px 10px; border-radius: 9999px; border: 1px solid #bbf7d0;">Anomaly Spikes</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Demo Account", key="btn_demo_launch"):
            u = db.login("demo@demo.com", "demo1234")
            if not u:
                uid, _ = db.register("Demo Student", "demo@demo.com", "demo1234")
                seed.seed(uid)
                u = db.login("demo@demo.com", "demo1234")
            st.session_state.user = u
            st.rerun()

    st.markdown("</div></div></div>", unsafe_allow_html=True)


if "user" not in st.session_state:
    auth_screen()
    st.stop()

user = st.session_state.user
uid = user["id"]
df = db.fetch_transactions(uid)
budgets = db.get_budgets(uid)

# Train categoriser on seed corpus + this user's own history
history = []
if not df.empty:
    e = df[(df["type"] == "expense") & (df["description"].str.len() > 2)]
    history = list(zip(e["description"].str.lower(), e["category"]))
ml.train(history)

# ---------------------------------------------------------------- Sidebar
st.sidebar.markdown(
    f"""
    <div class="sidebar-brand-box">
        <div class="sidebar-brand-eyebrow">PERSONAL FINANCE</div>
        <div class="sidebar-brand-title">Your money, in focus</div>
        <div class="sidebar-user-pill">
            <span class="sidebar-user-dot"></span>
            <span>{user['name']}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

PAGES = [
    "Dashboard",
    "Add Transaction",
    "Transactions",
    "Budgets",
    "Insights & Forecast",
    "People Ledger",
    "Import / Export",
]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

today = date.today()
if not df.empty:
    periods = sorted({(d.year, d.month) for d in df["date"]}, reverse=True)
else:
    periods = [(today.year, today.month)]
labels = [f"{calendar.month_name[m]} {y}" for y, m in periods]
sel = st.sidebar.selectbox("Period Filter", labels)
year, month = periods[labels.index(sel)]

st.sidebar.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
if st.sidebar.button("Log out"):
    del st.session_state["user"]
    st.rerun()

# ---------------------------------------------------------------- Page 1: Dashboard
if page == "Dashboard":
    render_header(
        eyebrow=f"OVERVIEW / {sel.upper()}",
        title="Your money, in focus",
        subtitle=f"Monthly snapshot for {sel}: spending categories, daily trends, and budget alerts.",
    )

    k = an.kpis(df, year, month)
    bs = an.budget_status(df, budgets, year, month)
    total_budget = sum(budgets.values())
    rem_budget = total_budget - k["spent"] if total_budget else None

    # Consistent Dark Hero + Secondary KPI Grid
    render_kpis(
        hero={
            "eyebrow": "TOTAL SPENT",
            "value": inr(k["spent"]),
            "badge": "Current Month",
            "subtext": f"{len(df[(df['type']=='expense') & (df['date'].dt.year==year) & (df['date'].dt.month==month)])} transactions",
        },
        secondaries=[
            {
                "eyebrow": "MONTHLY INCOME",
                "value": inr(k["income"]),
                "subtext": "Total received & credited",
            },
            {
                "eyebrow": "REMAINING BUDGET",
                "value": inr(rem_budget) if rem_budget is not None else "—",
                "badge": "Over Budget" if rem_budget is not None and rem_budget < 0 else "On Track",
                "badge_type": "danger" if rem_budget is not None and rem_budget < 0 else "good",
                "subtext": f"Out of {inr(total_budget)} target cap" if total_budget else "No budgets set",
            },
            {
                "eyebrow": "SAVINGS RATE",
                "value": f"{k['savings_rate']:.0f}%",
                "badge": "Healthy" if k["savings_rate"] >= 20 else "Low",
                "badge_type": "good" if k["savings_rate"] >= 20 else "warn",
                "subtext": f"{inr(k['saved'])} net surplus",
            },
        ],
    )

    # High-contrast Alert Banners
    for _, r in bs.iterrows():
        if r["status"] == "over":
            st.markdown(
                f'<div class="alert-banner danger">'
                f'<span style="font-size: 1.1rem;">🚨</span>'
                f'<div><strong>{r["category"]} budget exceeded:</strong> {inr(r["spent"])} spent of {inr(r["budget"])} limit ({r["pct"]:.0f}% utilized).</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif r["status"] == "warning":
            st.markdown(
                f'<div class="alert-banner warn">'
                f'<span style="font-size: 1.1rem;">⚠️</span>'
                f'<div><strong>{r["category"]} approaching limit:</strong> {r["pct"]:.0f}% of budget used ({inr(r["spent"])} of {inr(r["budget"])}).</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    m = an.month_slice(df, year, month)
    exp = m[m["type"] == "expense"]

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Spending by Category</h3>
            """,
            unsafe_allow_html=True,
        )
        cs = an.category_spend(df, year, month)
        if len(cs):
            cs_df = cs.reset_index()
            cs_df.columns = ["category", "amount"]

            # Fix Donut Chart:
            # 1. Darken labels to #1e293b (matches body text, eliminates low-contrast light gray)
            # 2. Slice size and legend colors strictly matched via CATEGORY_COLORS
            # 3. Rent visually dominates appropriately
            fig_donut = px.pie(
                cs_df,
                values="amount",
                names="category",
                hole=0.5,
                color="category",
                color_discrete_map=CATEGORY_COLORS,
            )
            fig_donut.update_traces(
                textposition="outside",
                textinfo="label+percent",
                textfont=dict(color="#1e293b", size=12, family="Inter, sans-serif"),
                outsidetextfont=dict(color="#1e293b", size=12, family="Inter, sans-serif"),
                insidetextfont=dict(color="#ffffff", size=11, family="Inter, sans-serif"),
                marker=dict(line=dict(color="#ffffff", width=2)),
                sort=True,
            )
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.28,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, color="#475569"),
                ),
                margin=dict(t=25, b=45, l=25, r=25),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                height=350,
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No expense transactions recorded for this month.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Daily Spending & Cumulative Trend</h3>
            """,
            unsafe_allow_html=True,
        )
        if len(exp):
            daily = exp.groupby(exp["date"].dt.date)["amount"].sum().reset_index()
            daily["cumulative"] = daily["amount"].cumsum()

            max_daily = float(daily["amount"].max()) if not daily.empty else 1000
            max_cum = float(daily["cumulative"].max()) if not daily.empty else 5000

            # Fix Broken Secondary Y-Axis:
            # 1. Synchronize tick counts (nticks=6) across both axes
            # 2. Clear title "Cumulative ₹" with distinct emerald styling
            # 3. showgrid=False on yaxis2 to prevent duplicate/overlapping grid lines
            # 4. Ample right margin (r=75) so tick numbers never overlap or clip
            fig_trend = go.Figure()
            fig_trend.add_bar(
                x=daily["date"],
                y=daily["amount"],
                name="Daily",
                marker_color="#334155",
                hovertemplate="<b>%{x}</b><br>Daily Spend: ₹%{y:,.0f}<extra></extra>",
            )
            fig_trend.add_scatter(
                x=daily["date"],
                y=daily["cumulative"],
                name="Cumulative",
                yaxis="y2",
                line=dict(color="#10b981", width=2.8),
                marker=dict(size=5, color="#10b981"),
                hovertemplate="Cumulative: ₹%{y:,.0f}<extra></extra>",
            )
            fig_trend.update_layout(
                margin=dict(l=55, r=75, t=30, b=40),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=11, color="#475569"),
                ),
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(size=11, color="#64748b"),
                    linecolor="#e2e8f0",
                ),
                yaxis=dict(
                    title=dict(text="Daily (₹)", font=dict(size=12, color="#475569")),
                    tickfont=dict(size=11, color="#64748b"),
                    tickprefix="₹",
                    showgrid=True,
                    gridcolor="#f1f5f9",
                    zeroline=True,
                    zerolinecolor="#e2e8f0",
                    range=[0, max_daily * 1.15],
                    nticks=6,
                ),
                yaxis2=dict(
                    title=dict(text="Cumulative ₹", font=dict(size=12, color="#059669")),
                    tickfont=dict(size=11, color="#059669"),
                    tickprefix="₹",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    zeroline=False,
                    range=[0, max_cum * 1.15],
                    nticks=6,
                ),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                hovermode="x unified",
                height=350,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No expense transactions recorded for this month.")
        st.markdown("</div>", unsafe_allow_html=True)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Budget Progress</h3>
            """,
            unsafe_allow_html=True,
        )
        if bs.empty:
            st.info("No category budgets set yet. Navigate to the Budgets page to establish limits.")
        for _, r in bs.iterrows():
            st.write(f"**{r['category']}** — {inr(r['spent'])} of {inr(r['budget'])} ({r['pct']:.0f}%)")
            st.progress(min(r["pct"] / 100, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b2:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Largest Purchases This Month</h3>
            """,
            unsafe_allow_html=True,
        )
        if len(exp):
            top = exp.nlargest(5, "amount")[["date", "description", "category", "amount"]].copy()
            top["date"] = top["date"].dt.date
            top["amount"] = top["amount"].apply(inr)
            top.columns = ["Date", "Description", "Category", "Amount"]
            st.dataframe(top, hide_index=True, use_container_width=True)
        else:
            st.info("No expenses found.")
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 2: Add Transaction
elif page == "Add Transaction":
    render_header(
        eyebrow="RECORD ENTRY / SMART PARSER",
        title="Add Transaction",
        subtitle="Log transactions using conversational natural language or traditional manual input.",
    )

    k = an.kpis(df, year, month)
    top_cat = an.category_spend(df, year, month).index[0] if len(an.category_spend(df, year, month)) else "None"

    render_kpis(
        hero={
            "eyebrow": "MONTHLY EXPENDITURE",
            "value": inr(k["spent"]),
            "badge": "Current Month",
            "subtext": f"{len(df)} total transactions logged in ledger",
        },
        secondaries=[
            {
                "eyebrow": "PRIMARY EXPENSE CATEGORY",
                "value": top_cat,
                "subtext": "Highest spending area this month",
            },
            {
                "eyebrow": "INCOME RECORDED",
                "value": inr(k["income"]),
                "subtext": "Surplus buffer available",
            },
        ],
    )

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">✨ Smart Entry (Natural Language Parser)</h3>
            <p style="color: #64748b; font-size: 0.88rem; margin-bottom: 12px;">
                Type conversational queries such as:
                <code>Zomato 340</code> &middot;
                <code>spent 250 on auto yesterday</code> &middot;
                <code>got 5000 pocket money on 12 oct</code> &middot;
                <code>paid 600 wifi bill 2 days ago</code>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("nl"):
        text = st.text_input("Enter natural expense description", placeholder="e.g. Swiggy 420 yesterday evening")
        go_parse = st.form_submit_button("Parse with NLP")

    if go_parse:
        p = ml.parse_entry(text, today)
        if p is None:
            st.error("Could not parse an amount. Please specify a number, e.g. 'Dinner 450'.")
        else:
            st.session_state.pending = p
            st.session_state.pcount = st.session_state.get("pcount", 0) + 1

    p = st.session_state.get("pending")
    pc = st.session_state.get("pcount", 0)
    if p:
        method_desc = {"rule": "Keyword Rule", "ml": "Naive Bayes ML Model", "default": "Fallback Classifier"}[p["method"]]
        st.markdown(
            f'<div class="alert-banner good">'
            f'<span>🤖</span>'
            f'<div><strong>AI Detected:</strong> {inr(p["amount"])} &middot; {p["type"].capitalize()} &middot; '
            f'<strong>{p["category"]}</strong> ({p["confidence"] * 100:.0f}% confidence via {method_desc}) &middot; {p["date"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        cats = db.CATEGORIES + ["Income"]
        c1, c2, c3 = st.columns(3)
        amt = c1.number_input("Amount (₹)", value=float(p["amount"]), min_value=0.0, key=f"p_amt_{pc}")
        cat = c2.selectbox(
            "Category", cats, index=cats.index(p["category"]) if p["category"] in cats else 0, key=f"p_cat_{pc}"
        )
        dte = c3.date_input("Date", value=p["date"], key=f"p_date_{pc}")
        desc = st.text_input("Description", value=p["description"], key=f"p_desc_{pc}")
        mode = st.selectbox("Payment mode", db.PAYMENT_MODES, key=f"p_mode_{pc}")

        if st.button("Save Parsed Transaction"):
            db.add_transaction(uid, dte, amt, p["type"], cat, desc, mode)
            st.session_state.pending = None
            st.toast("Transaction successfully saved!")
            st.rerun()

    st.markdown("<hr style='border: none; border-top: 1px solid #f1f5f9; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 class='section-heading'>Standard Manual Entry</h3>", unsafe_allow_html=True)

    with st.form("manual", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ttype = c1.radio("Transaction Type", ["expense", "income"], horizontal=True)
        amount = c2.number_input("Amount (₹)", min_value=0.0, step=10.0)
        c3, c4, c5 = st.columns(3)
        category = c3.selectbox("Category", db.CATEGORIES + ["Income"])
        dte = c4.date_input("Date", value=today)
        mode = c5.selectbox("Payment Mode", db.PAYMENT_MODES)
        desc = st.text_input("Description / Merchant")
        if st.form_submit_button("Add to Ledger"):
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(uid, dte, amount, ttype, category, desc, mode)
                st.success("Transaction added to ledger.")


# ---------------------------------------------------------------- Page 3: Transactions
elif page == "Transactions":
    render_header(
        eyebrow="AUDIT & RECORDS / ALL TIME",
        title="Transaction Records",
        subtitle="Search, filter, inspect, and update transactions stored in your local ledger.",
    )

    total_volume = df["amount"].sum() if not df.empty else 0.0
    exp_count = len(df[df["type"] == "expense"]) if not df.empty else 0
    inc_count = len(df[df["type"] == "income"]) if not df.empty else 0

    render_kpis(
        hero={
            "eyebrow": "TOTAL VOLUME TRACKED",
            "value": inr(total_volume),
            "badge": "All-Time",
            "subtext": f"{len(df)} total entries logged",
        },
        secondaries=[
            {
                "eyebrow": "EXPENSE ENTRIES",
                "value": str(exp_count),
                "subtext": "Outflow records",
            },
            {
                "eyebrow": "INCOME CREDITS",
                "value": str(inc_count),
                "subtext": "Inflow records",
            },
            {
                "eyebrow": "ACTIVE DATABASE",
                "value": "SQLite Local",
                "subtext": "Zero-cloud private store",
            },
        ],
    )

    if df.empty:
        st.info("No transactions logged yet.")
    else:
        f1, f2, f3 = st.columns(3)
        cat_f = f1.multiselect("Filter Category", sorted(df["category"].unique()))
        type_f = f2.selectbox("Filter Type", ["all", "expense", "income"])
        q = f3.text_input("Search Description")

        v = df.copy()
        if cat_f:
            v = v[v["category"].isin(cat_f)]
        if type_f != "all":
            v = v[v["type"] == type_f]
        if q:
            v = v[v["description"].str.contains(q, case=False, na=False)]

        v = v.head(300)[["id", "date", "type", "category", "description", "amount", "payment_mode"]].copy()
        v["date"] = v["date"].dt.date
        v["delete"] = False

        st.caption("Double-click any cell to edit. Mark 'delete' and click Apply to remove records.")
        edited = st.data_editor(
            v,
            hide_index=True,
            disabled=["id"],
            key="editor",
            use_container_width=True,
            column_config={
                "type": st.column_config.SelectboxColumn(options=["expense", "income"]),
                "category": st.column_config.SelectboxColumn(options=db.CATEGORIES + ["Income"]),
                "payment_mode": st.column_config.SelectboxColumn(options=db.PAYMENT_MODES),
                "date": st.column_config.DateColumn(),
                "amount": st.column_config.NumberColumn(format="₹%.0f"),
            },
        )

        if st.button("Apply edits / deletions"):
            n_upd = n_del = 0
            orig = v.set_index("id")
            for _, r in edited.iterrows():
                if r["delete"]:
                    db.delete_transaction(int(r["id"]), uid)
                    n_del += 1
                elif not r.drop("id").equals(orig.loc[r["id"]]):
                    db.update_transaction(
                        int(r["id"]), uid, r["date"], r["amount"], r["type"], r["category"], r["description"], r["payment_mode"]
                    )
                    n_upd += 1
            st.success(f"Updated {n_upd} entries; removed {n_del} entries.")
            st.rerun()


# ---------------------------------------------------------------- Page 4: Budgets
elif page == "Budgets":
    render_header(
        eyebrow=f"SPENDING TARGETS / {sel.upper()}",
        title="Monthly Budgets",
        subtitle="Establish monthly category spending caps and review threshold consumption.",
    )

    k = an.kpis(df, year, month)
    bs = an.budget_status(df, budgets, year, month)
    total_budget = sum(budgets.values())
    pct_used = (k["spent"] / total_budget * 100) if total_budget > 0 else 0.0
    alerts_count = len(bs[bs["status"] != "ok"]) if not bs.empty else 0

    render_kpis(
        hero={
            "eyebrow": "TOTAL BUDGET ALLOCATED",
            "value": inr(total_budget),
            "badge": f"{len(budgets)} Categories",
            "subtext": f"{pct_used:.0f}% utilized this month",
        },
        secondaries=[
            {
                "eyebrow": "TOTAL SPENT",
                "value": inr(k["spent"]),
                "subtext": "Realized expenditures",
            },
            {
                "eyebrow": "REMAINING HEADROOM",
                "value": inr(max(0, total_budget - k["spent"])),
                "subtext": "Unspent budget allowance",
            },
            {
                "eyebrow": "CATEGORIES AT RISK",
                "value": str(alerts_count),
                "badge": f"{alerts_count} Flagged" if alerts_count > 0 else "All Healthy",
                "badge_type": "danger" if alerts_count > 0 else "good",
                "subtext": "Warning or exceeded limits",
            },
        ],
    )

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">Set Category Budget Limits (₹)</h3>
        """,
        unsafe_allow_html=True,
    )
    with st.form("budgets"):
        cols = st.columns(2)
        new = {}
        for i, c in enumerate(db.CATEGORIES):
            new[c] = cols[i % 2].number_input(c, min_value=0.0, step=100.0, value=float(budgets.get(c, 0.0)))
        if st.form_submit_button("Save Budget Caps"):
            for c, val in new.items():
                if val > 0:
                    db.set_budget(uid, c, val)
            st.success("Budgets successfully updated.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not bs.empty:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Budget vs Realized Spend</h3>
            """,
            unsafe_allow_html=True,
        )
        fig_b = go.Figure()
        fig_b.add_bar(
            x=bs["category"],
            y=bs["budget"],
            name="Budget Target",
            marker_color="#94a3b8",
            hovertemplate="<b>%{x}</b><br>Budget: ₹%{y:,.0f}<extra></extra>",
        )
        fig_b.add_bar(
            x=bs["category"],
            y=bs["spent"],
            name="Spent so far",
            marker_color=[STATUS_COLORS[s] for s in bs["status"]],
            hovertemplate="<b>%{x}</b><br>Spent: ₹%{y:,.0f}<extra></extra>",
        )
        fig_b.update_layout(
            barmode="group",
            margin=dict(t=30, b=40, l=40, r=20),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(tickfont=dict(size=11, color="#475569")),
            yaxis=dict(tickprefix="₹", gridcolor="#f1f5f9"),
            height=360,
        )
        st.plotly_chart(fig_b, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 5: Insights & Forecast
elif page == "Insights & Forecast":
    render_header(
        eyebrow=f"INTELLIGENCE & PREDICTIONS / {sel.upper()}",
        title="Financial Insights & Forecast",
        subtitle="Predictive month-end projections, unusual anomaly detection, and 50/30/20 diagnostic check.",
    )

    k = an.kpis(df, year, month)
    proj, total_proj = an.forecast_month_end(df, year, month, today)
    an_df = an.detect_anomalies(df)
    over_pace = sum(1 for c, p in proj.items() if budgets.get(c) and p > budgets[c])

    render_kpis(
        hero={
            "eyebrow": "PROJECTED MONTH-END SPEND",
            "value": inr(total_proj),
            "badge": "Blended Run-Rate + ML",
            "subtext": f"Estimated total for {sel}",
        },
        secondaries=[
            {
                "eyebrow": "CURRENT SPENT",
                "value": inr(k["spent"]),
                "subtext": "Realized to date",
            },
            {
                "eyebrow": "CATEGORIES OVER PACE",
                "value": str(over_pace),
                "badge": f"{over_pace} at Risk" if over_pace > 0 else "All on Pace",
                "badge_type": "warn" if over_pace > 0 else "good",
                "subtext": "Exceeding budget velocity",
            },
            {
                "eyebrow": "ANOMALIES DETECTED",
                "value": str(len(an_df)),
                "badge": "Modified Z-Score",
                "badge_type": "danger" if len(an_df) > 0 else "good",
                "subtext": "Outlier purchases flagged",
            },
        ],
    )

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">Smart Recommendations & Observations</h3>
        """,
        unsafe_allow_html=True,
    )
    for level, msg in an.insights(df, budgets, year, month, today):
        cls_map = {"danger": "danger", "warn": "warn", "good": "good", "info": "info"}
        st.markdown(
            f'<div class="alert-banner {cls_map.get(level, "info")}">'
            f'<span>{LEVEL_ICON.get(level, "ℹ️")}</span>'
            f'<div>{msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Month-End Category Forecast</h3>
            """,
            unsafe_allow_html=True,
        )
        if proj:
            rows = []
            spent = an.category_spend(df, year, month)
            for c, p in sorted(proj.items(), key=lambda x: -x[1]):
                lim = budgets.get(c)
                rows.append(
                    {
                        "Category": c,
                        "Spent so Far": inr(spent.get(c, 0)),
                        "Projected Month-End": inr(p),
                        "Budget": inr(lim) if lim else "—",
                        "Status": "—" if not lim else ("⚠️ Will exceed" if p > lim else "✅ On track"),
                    }
                )
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.caption("Forecast formula: 50% daily run-rate extrapolation + 50% linear regression on cumulative spend.")
        else:
            st.info("Insufficient data for reliable month-end projection.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_f2:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Unusual Transactions (Anomaly Detection)</h3>
            """,
            unsafe_allow_html=True,
        )
        if an_df.empty:
            st.success("No anomalous spending spikes detected.")
        else:
            show = an_df.head(10)[["date", "description", "category", "amount", "typical", "zscore"]].copy()
            show["date"] = show["date"].dt.date
            show["amount"] = show["amount"].apply(inr)
            show["typical"] = show["typical"].apply(inr)
            show.columns = ["Date", "Description", "Category", "Amount", "Typical Range", "Outlier Score"]
            st.dataframe(show.round(1), hide_index=True, use_container_width=True)
            st.caption("Method: Modified Z-score (median/MAD > 3.5) and >= 3x typical peer spending.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">Classifier Model Accuracy Benchmark</h3>
        """,
        unsafe_allow_html=True,
    )
    acc, n_test = ml.model_accuracy(history)
    st.write(
        f"Evaluated on **{n_test} held-out hand-labelled test phrases** (never used during training): "
        f"**{acc * 100:.1f}% accuracy** using hybrid rule-matching and multinomial Naive Bayes."
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 6: People Ledger
elif page == "People Ledger":
    render_header(
        eyebrow="COUNTERPARTY TRACKING / PEER-TO-PEER",
        title="People Ledger",
        subtitle="UPI peer transfers: identify who you sent money to, who repaid you, and your net balance.",
    )

    scope = st.radio("Calculation Scope", ["Selected month", "All time"], horizontal=True)
    led = an.people_ledger(df, year, month) if scope == "Selected month" else an.people_ledger(df)

    sent_total = led["sent"].sum() if not led.empty else 0.0
    rec_total = led["received"].sum() if not led.empty else 0.0
    net_total = rec_total - sent_total

    render_kpis(
        hero={
            "eyebrow": "TOTAL SENT TO PEOPLE",
            "value": inr(sent_total),
            "badge": "UPI Transfers Out",
            "subtext": f"{len(led)} contacts tracked",
        },
        secondaries=[
            {
                "eyebrow": "TOTAL RECEIVED BACK",
                "value": inr(rec_total),
                "subtext": "UPI inflow credits",
            },
            {
                "eyebrow": "NET POSITION",
                "value": inr(abs(net_total)),
                "badge": "You are Owed" if net_total >= 0 else "You Paid More",
                "badge_type": "good" if net_total >= 0 else "warn",
                "subtext": "Net settlement balance",
            },
            {
                "eyebrow": "COUNTERPARTIES",
                "value": str(len(led)),
                "subtext": "Unique individuals",
            },
        ],
    )

    if led.empty:
        st.info("No peer-to-peer or contact transfer records found.")
    else:
        st.markdown(
            """
            <div class="section-card">
                <h3 class="section-heading">Net Balance per Contact (₹)</h3>
            """,
            unsafe_allow_html=True,
        )
        top = led.head(12).copy()
        top["direction"] = top["net"].apply(lambda v: "You are owed" if v > 0 else "You paid more")
        fig_p = px.bar(
            top,
            x="net",
            y="person",
            orientation="h",
            color="direction",
            color_discrete_map={"You are owed": "#059669", "You paid more": "#dc2626"},
        )
        fig_p.update_layout(
            yaxis=dict(autorange="reversed", tickfont=dict(size=12, color="#1e293b")),
            xaxis=dict(title="Net Balance (₹)", gridcolor="#f1f5f9"),
            margin=dict(t=20, b=40, l=40, r=20),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            height=360,
        )
        st.plotly_chart(fig_p, use_container_width=True)

        show = led.copy()
        show["sent"] = show["sent"].apply(inr)
        show["received"] = show["received"].apply(inr)
        show["net"] = show["net"].apply(inr)
        show.columns = ["Contact / Person", "Sent ₹", "Received ₹", "Net Balance ₹", "Transactions Count"]
        st.dataframe(show, hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Page 7: Import / Export
elif page == "Import / Export":
    render_header(
        eyebrow="DATA PORTABILITY / BACKUP & SYNC",
        title="Import & Export Data",
        subtitle="Ingest bank or UPI statements and export structured reports in CSV or Excel.",
    )

    render_kpis(
        hero={
            "eyebrow": "STORED TRANSACTIONS",
            "value": str(len(df)),
            "badge": "Active Records",
            "subtext": "Local offline SQLite database",
        },
        secondaries=[
            {
                "eyebrow": "MONTHLY PERIODS",
                "value": str(len(periods)),
                "subtext": "Distinct months recorded",
            },
            {
                "eyebrow": "EXPORT FORMATS",
                "value": "CSV + XLSX",
                "subtext": "Compatible with Excel, Sheets",
            },
            {
                "eyebrow": "STORAGE SECURITY",
                "value": "Encrypted PBKDF2",
                "subtext": "Salted password hashing",
            },
        ],
    )

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">Import Bank Statement (CSV or Excel)</h3>
            <p style="color: #64748b; font-size: 0.88rem; margin-bottom: 14px;">
                Compatible with statements containing Date, Narration, Withdrawal/Debit, and Deposit/Credit columns.
                UPI IDs and reference numbers are cleaned automatically.
            </p>
        """,
        unsafe_allow_html=True,
    )
    up = st.file_uploader("Upload bank statement", type=["csv", "xlsx", "xls"])
    if up is not None:
        try:
            parsed, notes = imp.parse_statement(up, up.name)
            for n in notes:
                st.info(n)
            parsed["category"] = [
                "Income" if t == "income" else ml.categorize(d or r)[0]
                for d, r, t in zip(parsed["description"], parsed["description_raw"], parsed["type"])
            ]
            st.write(f"Detected **{len(parsed)}** transactions. Verify categories before importing:")
            cats = db.CATEGORIES + ["Income"]
            review = st.data_editor(
                parsed[["date", "description", "amount", "type", "category"]],
                hide_index=True,
                key="imp_editor",
                use_container_width=True,
                column_config={
                    "category": st.column_config.SelectboxColumn(options=cats),
                    "type": st.column_config.SelectboxColumn(options=["expense", "income"]),
                },
            )
            if st.button(f"Confirm & Import {len(review)} Transactions"):
                rows = [
                    dict(
                        date=r["date"],
                        amount=float(r["amount"]),
                        type=r["type"],
                        category=r["category"],
                        description=r["description"],
                        payment_mode="UPI",
                    )
                    for _, r in review.iterrows()
                ]
                db.add_many(uid, rows)
                st.success("Successfully imported transactions into your ledger!")
                st.rerun()
        except Exception as ex:
            st.error(f"Could not parse file: {ex}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <h3 class="section-heading">Export Reports</h3>
            <p style="color: #64748b; font-size: 0.88rem; margin-bottom: 14px;">
                Download your transaction ledger and monthly breakdown for record-keeping.
            </p>
        """,
        unsafe_allow_html=True,
    )
    if df.empty:
        st.info("No transaction data available to export.")
    else:
        out = df.drop(columns=["user_id"]).copy()
        out["date"] = out["date"].dt.date
        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            st.download_button("Download CSV Ledger", out.to_csv(index=False), "transactions.csv", "text/csv")
        with c_exp2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                out.to_excel(xw, sheet_name="Transactions", index=False)
                an.category_spend(df, year, month).rename("Spent").to_frame().to_excel(
                    xw, sheet_name=f"Summary {sel}"[:31]
                )
                an.budget_status(df, budgets, year, month).to_excel(xw, sheet_name="Budget status", index=False)
            st.download_button(
                "Download Excel Report (.xlsx)",
                buf.getvalue(),
                f"report_{year}_{month:02d}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Reload demo dataset"):
        seed.seed(uid)
        st.toast("Demo data reloaded.")
        st.rerun()
