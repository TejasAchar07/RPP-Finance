import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from sklearn.linear_model import LinearRegression
import numpy as np
import io
import base64
from datetime import datetime, timedelta
import sys
import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transactions.db')

# Theme options for light and dark mode
THEMES = {
    'Light': dbc.themes.BOOTSTRAP,
    'Dark': dbc.themes.CYBORG
}

def get_theme():
    from urllib.parse import parse_qs
    import flask
    if flask.has_request_context():
        args = flask.request.args
        theme = args.get('theme', 'Light')
        return THEMES.get(theme, THEMES['Light'])
    return THEMES['Light']

app = dash.Dash(__name__, external_stylesheets=[get_theme(), "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"], suppress_callback_exceptions=True)
# Configure for production deployment
app.config.suppress_callback_exceptions = True
# Initialize DB if not exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        transation_type TEXT,
        amount REAL,
        type TEXT,
        description TEXT,
        date TEXT,
        title TEXT,
        UNIQUE(transation_type, amount, type, description, date, title)
    )''')
    conn.commit()
    conn.close()

init_db()

# Helper to insert data, check for duplicates, and clear DB
def insert_transactions(df):
    df = df.copy()
    df['date'] = df['date'].astype(str)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Check for duplicates
    placeholders = ','.join(['?']*6)
    unique_rows = []
    duplicate_rows = []
    for row in df.itertuples(index=False):
        c.execute(f'SELECT 1 FROM transactions WHERE transation_type=? AND amount=? AND type=? AND description=? AND date=? AND title=?', row)
        if c.fetchone():
            duplicate_rows.append(row)
        else:
            unique_rows.append(row)
    if unique_rows:
        c.executemany(f'INSERT INTO transactions VALUES (?,?,?,?,?,?)', unique_rows)
    conn.commit()
    conn.close()
    return duplicate_rows

def overwrite_duplicates(df):
    df = df.copy()
    df['date'] = df['date'].astype(str)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for row in df.itertuples(index=False):
        c.execute('''DELETE FROM transactions WHERE transation_type=? AND amount=? AND type=? AND description=? AND date=? AND title=?''', row)
        c.execute('''INSERT INTO transactions VALUES (?,?,?,?,?,?)''', row)
    conn.commit()
    conn.close()

def clear_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM transactions')
    conn.commit()
    conn.close()

def fetch_transactions(start_date=None, end_date=None, transation_type=None, type_filter=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = 'SELECT * FROM transactions WHERE 1=1'
    params = []
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    if transation_type:
        query += ' AND transation_type IN (%s)' % ','.join(['?']*len(transation_type))
        params.extend(transation_type)
    if type_filter:
        query += ' AND type IN (%s)' % ','.join(['?']*len(type_filter))
        params.extend(type_filter)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    columns = ['transation_type', 'amount', 'type', 'description', 'date', 'title']
    return pd.DataFrame(rows, columns=columns)

def send_email_notification(emails, subject, body, smtp_server="smtp.gmail.com", smtp_port=587, sender_email=None, sender_password=None):
    """
    Send email notification to multiple recipients
    """
    if not sender_email or not sender_password:
        return False, "SMTP credentials not configured"
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(emails)
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, emails, text)
        server.quit()
        
        return True, f"Email sent successfully to {len(emails)} recipients"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Helper to build theme toggle link
def theme_toggle_row():
    import flask
    args = flask.request.args if flask.has_request_context() else {}
    current_theme = args.get('theme', 'Light')
    other_theme = 'Dark' if current_theme == 'Light' else 'Light'
    url = f"?theme={other_theme}"
    return dbc.Row([
        dbc.Col([
            html.A(
                f"Switch to {other_theme} Mode",
                href=url,
                className="btn btn-outline-secondary mb-3",
                style={"width": "200px"}
            )
        ], width=12, className="text-center")
    ])

CARD_STYLE = {
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
    "borderRadius": "12px",
    "marginBottom": "32px",
    "background": "#fff",
    "padding": "32px 24px"
}
DARK_CARD_STYLE = {
    "boxShadow": "0 2px 8px rgba(0,0,0,0.32)",
    "borderRadius": "12px",
    "marginBottom": "32px",
    "background": "#23272b",
    "padding": "32px 24px"
}

BG_STYLE = {
    "background": "#f4f6fa",
    "minHeight": "100vh",
    "paddingBottom": "40px"
}
DARK_BG_STYLE = {
    "background": "#181a1b",
    "minHeight": "100vh",
    "paddingBottom": "40px"
}

# Update summary card style for more height, better spacing, and perfect content fit
SUMMARY_CARD_STYLE = {
    "background": "#fff",
    "color": "#222",
    "borderRadius": "20px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
    "border": "1px solid #e0e0e0",
    "marginBottom": "0",
    "minHeight": "200px",
    "maxHeight": "200px",
    "width": "100%",
    "height": "100%",
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "visible"
}
CARD_CONTENT_STYLE = {
    "padding": "18px",
    "width": "100%",
    "height": "100%",
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center",
    "justifyContent": "space-between"
}

def serve_layout():
    import flask
    args = flask.request.args if flask.has_request_context() else {}
    current_theme = args.get('theme', 'Light')
    card_style = CARD_STYLE if current_theme == 'Light' else DARK_CARD_STYLE
    bg_style = BG_STYLE if current_theme == 'Light' else DARK_BG_STYLE
    summary_card_style = SUMMARY_CARD_STYLE
    # Choose icon based on theme
    theme_icon = "bi-moon" if current_theme == 'Light' else "bi-sun"
    theme_label = "Switch to Dark Mode" if current_theme == 'Light' else "Switch to Light Mode"
    theme_url = f"?theme={'Dark' if current_theme == 'Light' else 'Light'}"
    # App logo/icon (use a finance or analytics icon)
    app_logo = html.I(className="bi bi-bar-chart-fill", style={"fontSize": "2.2rem", "color": "#198754", "marginRight": "16px"})
    header_style = {
        "background": "#f8f9fa",
        "borderBottom": "1px solid #e0e0e0",
        "padding": "18px 0 12px 0",
        "marginBottom": "0.5rem",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.04)",
        "width": "100%"
    }
    now = datetime.now()
    first_of_month = datetime(now.year, now.month, 1)
    today = now.date()
    min_date_allowed = datetime(2000, 1, 1)
    return html.Div([
        # Styled header with logo, title, and theme toggle
        html.Header([
            html.Div([
                app_logo,
                html.Span("Personal Finance Dashboard", className="fw-bold", style={"fontSize": "2rem", "color": "#222", "verticalAlign": "middle"}),
                html.A([
                    html.I(className=f"bi {theme_icon}", style={"fontSize": "1.7rem", "marginLeft": "18px"}),
                ], href=theme_url, title=theme_label, style={"float": "right", "color": "#888", "verticalAlign": "middle"})
            ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "width": "100%", "padding": "0 32px"})
        ], style=header_style),
        # Unified top control bar: filters + upload/download in one card
        dbc.Card(
            dbc.Row([
                dbc.Col([
                    html.Label("Transaction Type", className="fw-bold mb-1"),
                    dcc.Dropdown(id='filter-transation_type', options=[], multi=True, disabled=True, placeholder="Filter by transaction type"),
                ], xs=12, sm=6, md=3, lg=3, xl=3, className="mb-2"),
                dbc.Col([
                    html.Label("Type", className="fw-bold mb-1"),
                    dcc.Dropdown(id='filter-type', options=[], multi=True, disabled=True, placeholder="Filter by type"),
                ], xs=12, sm=6, md=3, lg=3, xl=3, className="mb-2"),
                dbc.Col([
                    html.Label("Trend Granularity", className="fw-bold mb-1"),
                    dcc.Dropdown(
                        id='trend-granularity',
                        options=[
                            {'label': 'Per Day', 'value': 'D'},
                            {'label': 'Per Month', 'value': 'ME'},
                            {'label': 'Per Quarter', 'value': 'Q'},
                            {'label': 'Per Year', 'value': 'YE'}
                        ],
                        value='ME',
                        clearable=False,
                        disabled=True,
                        placeholder="Select granularity"
                    )
                ], xs=12, sm=12, md=3, lg=3, xl=3, className="mb-2"),
                dbc.Col([
                    html.Label("Date Range", className="fw-bold mb-1"),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=min_date_allowed,
                        max_date_allowed=None,
                        start_date=first_of_month,
                        end_date=today,
                        start_date_placeholder_text="Start Date",
                        end_date_placeholder_text="End Date",
                        disabled=True
                    )
                ], xs=12, sm=12, md=3, lg=3, xl=3, className="mb-2"),
                dbc.Col([
                    dbc.Row([
                        dbc.Col(
                            dcc.Upload(
                                id='upload-data',
                                children=dbc.Button([
                                    html.I(className="bi bi-upload me-2"),
                                    "Upload Excel"
                                ], color="primary", className="w-100"),
                                style={'display': 'inline-block', 'width': '100%'},
                                multiple=False
                            ), width="auto", className="me-2"
                        ),
                        dbc.Col(
                            dbc.Button([
                                html.I(className="bi bi-download me-2"),
                                "Download Template"
                            ], id="btn-download-template", color="warning", className="w-100"),
                            width="auto", className="me-2"
                        ),
                        dbc.Col(
                            dbc.Button("Clear Database", id="btn-clear-db", color="danger", className="w-100"),
                            width="auto", className="me-2"
                        ),
                        dbc.Col(
                            dbc.Button([
                                html.I(className="bi bi-envelope me-2"),
                                "Send Email"
                            ], id="btn-open-email", color="info", className="w-100"),
                            width="auto"
                        ),
                        # Hidden download component for callback
                        dcc.Download(id="download-template"),
                    ], className="g-2 align-items-center mb-2", style={"flexWrap": "nowrap"}),
                ], xs=12, sm=12, md=3, lg=3, xl=3, className="mb-2"),
            ], align="center", className="g-3"),
            body=True,
            className="mb-4 p-3 shadow-sm",
            style={"background": "#f8f9fa", "borderRadius": "16px"}
        ),
        # Restore summary cards row
        dbc.Row([
            dbc.Col(html.Div(id="card-highest-income", n_clicks=0), width=2, className="d-flex flex-column align-items-stretch p-0 h-100", style={"marginRight": "18px", "cursor": "pointer"}),
            dbc.Col(html.Div(id="card-highest-expense", n_clicks=0), width=2, className="d-flex flex-column align-items-stretch p-0 h-100", style={"marginRight": "18px", "cursor": "pointer"}),
            dbc.Col(html.Div(id="card-total", n_clicks=0), width=2, className="d-flex flex-column align-items-stretch p-0 h-100", style={"marginRight": "18px", "cursor": "pointer"}),
            dbc.Col(html.Div(id="card-profitloss", n_clicks=0), width=2, className="d-flex flex-column align-items-stretch p-0 h-100", style={"marginRight": "18px", "cursor": "pointer"}),
            dbc.Col(html.Div(id="card-frequent", n_clicks=0), width=2, className="d-flex flex-column align-items-stretch p-0 h-100", style={"cursor": "pointer"}),
        ], className="mb-4 mt-2 justify-content-center gx-4", style={"maxWidth": "90vw", "margin": "0 auto"}),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Breakdown"), close_button=True),
            dbc.ModalBody(dcc.Graph(id='summary-pie', style={"height": "320px"})),
        ], id='summary-pie-modal', is_open=False, centered=True, size="md", backdrop=True),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Your Uploaded Data Table", className="mt-2 text-center"),
                        html.P("This table shows all the data from your uploaded Excel file.", className="text-center"),
                        html.Div(id='table-container', className="mb-3")
                    ])
                ], style=card_style)
            ], width=10, className="offset-md-1")
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Spending, Income, and Investment Trend", className="mt-2 text-center"),
                        html.P("This line chart shows how your total amount changes over time based on your selection above.", className="text-center"),
                        dcc.Graph(id='trend-graph', config={'displayModeBar': False}, className="mb-3")
                    ])
                ], style=card_style)
            ], width=10, className="offset-md-1")
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Future Projection (Prediction)", className="mt-2 text-center"),
                        html.P("This chart predicts your future total amount based on your past data. The dotted line shows the estimated trend.", className="text-center"),
                        dcc.Graph(id='projection-graph', config={'displayModeBar': False}, className="mb-3")
                    ])
                ], style=card_style)
            ], width=10, className="offset-md-1")
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("All Transactions Overview", className="mt-2 text-center"),
                        html.P("This scatter plot shows every transaction by date, amount, and type. Hover over points to see details.", className="text-center"),
                        dcc.Graph(id='all-data-graph', config={'displayModeBar': False}, className="mb-3")
                    ])
                ], style=card_style)
            ], width=10, className="offset-md-1")
        ]),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Duplicate Entries Detected"), close_button=False),
            dbc.ModalBody([
                html.Div("Some entries in your upload already exist in the database. Do you want to overwrite them or cancel the import?"),
                html.Div(id="duplicate-list", style={"maxHeight": "200px", "overflowY": "auto", "fontSize": "0.9rem", "marginTop": "1rem"})
            ]),
            dbc.ModalFooter([
                dbc.Button("Overwrite", id="btn-overwrite", color="warning", className="me-2", n_clicks=0),
                dbc.Button("Cancel Import", id="btn-cancel-import", color="secondary", n_clicks=0)
            ])
        ], id="modal-duplicates", is_open=False, centered=True),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirm Clear Database"), close_button=False),
            dbc.ModalBody("Are you sure you want to delete all transactions? This action cannot be undone."),
            dbc.ModalFooter([
                dbc.Button("Yes, Clear All", id="btn-confirm-clear", color="danger", className="me-2", n_clicks=0),
                dbc.Button("Cancel", id="btn-cancel-clear", color="secondary", n_clicks=0)
            ])
        ], id="modal-clear-db", is_open=False, centered=True),
        # Email Notification Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Send Email Notification"), close_button=True),
            dbc.ModalBody([
                html.Div([
                    html.Label("SMTP Configuration", className="fw-bold mb-2"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("SMTP Server", className="form-label"),
                            dbc.Input(id="smtp-server", type="text", value="smtp.gmail.com", disabled=True)
                        ], width=6),
                        dbc.Col([
                            html.Label("SMTP Port", className="form-label"),
                            dbc.Input(id="smtp-port", type="number", value=587, disabled=True)
                        ], width=6)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Sender Email (Gmail)", className="form-label"),
                            dbc.Input(id="sender-email", type="email", placeholder="your-email@gmail.com")
                        ], width=6),
                        dbc.Col([
                            html.Label("Gmail App Password", className="form-label"),
                            dbc.Input(id="sender-password", type="password", placeholder="Your Gmail app password")
                        ], width=6)
                    ], className="mb-3"),
                    html.Hr(),
                    html.Div([
                        html.I(className="bi bi-info-circle me-2"),
                        html.Span("Note: For Gmail, you need to use an App Password, not your regular password. Generate one in your Google Account settings under Security > 2-Step Verification > App passwords.", className="text-muted small")
                    ], className="mb-3 p-2 bg-light rounded"),
                    html.Label("Email Content", className="fw-bold mb-2"),
                    html.Label("Recipient Emails (one per line)", className="form-label"),
                    dbc.Textarea(id="recipient-emails", placeholder="email1@example.com\nemail2@example.com\nemail3@example.com", rows=3, className="mb-3"),
                    html.Label("Subject", className="form-label"),
                    dbc.Input(id="email-subject", type="text", placeholder="New Financial Data Published", value="New Financial Data Published", className="mb-3"),
                    html.Label("Message Body", className="form-label"),
                    dbc.Textarea(id="email-body", value="Dear team,\n\nNew financial data has been uploaded to the Personal Finance Dashboard.\n\nKey highlights:\n• Updated transaction records\n• Latest financial insights\n• Trend analysis and projections\n\nPlease review the updated information at your convenience.\n\nBest regards,\nFinance Team", rows=6, className="mb-3"),
                    html.Div(id="email-status", className="mt-3")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Send Email", id="btn-send-email", color="primary", className="me-2"),
                dbc.Button("Close", id="btn-close-email", color="secondary")
            ])
        ], id="modal-email", is_open=False, centered=True, size="lg"),
    ], style=bg_style)

app.layout = serve_layout

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None
    except Exception as e:
        print(e)
        return None
    return df

@app.callback(
    [Output('filter-transation_type', 'options'),
     Output('filter-type', 'options'),
     Output('filter-transation_type', 'disabled'),
     Output('filter-type', 'disabled'),
     Output('trend-granularity', 'disabled'),
     Output('date-range', 'disabled'),
     Output('card-highest-income', 'children'),
     Output('card-highest-expense', 'children'),
     Output('card-total', 'children'),
     Output('card-profitloss', 'children'),
     Output('card-frequent', 'children'),
     Output('table-container', 'children'),
     Output('trend-graph', 'figure'),
     Output('projection-graph', 'figure'),
     Output('all-data-graph', 'figure'),
     Output('modal-clear-db', 'is_open'),
     Output('modal-duplicates', 'is_open'),
     Output('duplicate-list', 'children')],
    [Input('upload-data', 'contents'),
     Input('trend-granularity', 'value'),
     Input('filter-transation_type', 'value'),
     Input('filter-type', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('btn-clear-db', 'n_clicks'),
     Input('btn-confirm-clear', 'n_clicks'),
     Input('btn-cancel-clear', 'n_clicks'),
     Input('btn-overwrite', 'n_clicks'),
     Input('btn-cancel-import', 'n_clicks')],
    [State('upload-data', 'filename'),
     State('modal-clear-db', 'is_open'),
     State('modal-duplicates', 'is_open'),
     State('upload-data', 'contents')]
)
def update_output(contents, granularity, transation_type, type_filter, start_date, end_date, btn_clear_db, btn_confirm_clear, btn_cancel_clear, btn_overwrite, btn_cancel_import, filename, modal_clear_open, modal_dup_open, last_upload_contents):
    import flask
    from dash import callback_context
    args = flask.request.args if flask.has_request_context() else {}
    summary_card_style = SUMMARY_CARD_STYLE
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else ''
    # Handle clear DB modal logic
    if triggered.startswith('btn-clear-db'):
        return [dash.no_update] * 15 + [True, False, None]
    if triggered.startswith('btn-cancel-clear'):
        return [dash.no_update] * 15 + [False, False, None]
    if triggered.startswith('btn-confirm-clear'):
        clear_db()
        return [[], [], True, True, True, True, None, None, None, None, None, None, go.Figure(), go.Figure(), go.Figure(), False, False, None]
    # Handle duplicate modal logic
    if triggered.startswith('btn-cancel-import'):
        return [dash.no_update] * 15 + [False, False, None]
    if triggered.startswith('btn-overwrite'):
        # Overwrite duplicates with last uploaded data
        if last_upload_contents and filename:
            df_upload = parse_contents(last_upload_contents, filename)
            if df_upload is not None and set(['transation_type', 'amount', 'type', 'description', 'date', 'title']).issubset(df_upload.columns):
                df_upload['date'] = pd.to_datetime(df_upload['date'])
                overwrite_duplicates(df_upload)
        # After overwrite, fetch and show data
        df = fetch_transactions(start_date, end_date, transation_type, type_filter)
        if df is None or df.empty:
            return [[], [], True, True, True, True, None, None, None, None, None, html.Div("No data available. Upload a file to get started."), go.Figure(), go.Figure(), go.Figure(), False, False, None]
        df['date'] = pd.to_datetime(df['date'])
        # Prepare filter options
        transation_type_options = [{'label': str(val), 'value': val} for val in sorted(df['transation_type'].dropna().unique())]
        type_options = [{'label': str(val), 'value': val} for val in sorted(df['type'].dropna().unique())]
        # --- Summary Analysis ---
        income_df = df[df['transation_type'] == 'income']
        expense_df = df[df['transation_type'] == 'expense']
        highest_income = income_df['amount'].max() if not income_df.empty else 0
        highest_income_row = income_df.loc[income_df['amount'].idxmax()] if not income_df.empty else None
        highest_expense = expense_df['amount'].max() if not expense_df.empty else 0
        highest_expense_row = expense_df.loc[expense_df['amount'].idxmax()] if not expense_df.empty else None
        accent_style_income = {"width": "16px", "height": "16px", "borderRadius": "50%", "background": "#198754", "display": "inline-block", "marginRight": "8px"}
        accent_style_expense = {"width": "16px", "height": "16px", "borderRadius": "50%", "background": "#dc3545", "display": "inline-block", "marginRight": "8px"}
        accent_style_profit = {"width": "32px", "height": "32px", "borderRadius": "50%", "background": "#ffc107", "display": "inline-block", "marginRight": "12px"}
        accent_style_freq = {"width": "32px", "height": "32px", "borderRadius": "50%", "background": "#0dcaf0", "display": "inline-block", "marginRight": "12px"}
        card_highest_income = html.Div([
            html.Div([
                html.Div([
                    html.Span("", style={**accent_style_income, "verticalAlign": "middle"}),
                    html.Span("Highest Income", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
                html.Div(f"₹{highest_income:,.2f}" if highest_income else "-", className="fw-bold text-center", style={"color": "#198754", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
                html.Small(highest_income_row['title'] if highest_income_row is not None and 'title' in highest_income_row else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "fontStyle": "italic"}),
                html.Small(highest_income_row['description'] if highest_income_row is not None else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
            ], style=CARD_CONTENT_STYLE)
        ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
        card_highest_expense = html.Div([
            html.Div([
                html.Div([
                    html.Span("", style={**accent_style_expense, "verticalAlign": "middle"}),
                    html.Span("Highest Expense", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
                html.Div(f"₹{highest_expense:,.2f}" if highest_expense else "-", className="fw-bold text-center", style={"color": "#dc3545", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
                html.Small(highest_expense_row['title'] if highest_expense_row is not None and 'title' in highest_expense_row else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "fontStyle": "italic"}),
                html.Small(highest_expense_row['description'] if highest_expense_row is not None else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
            ], style=CARD_CONTENT_STYLE)
        ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
        total_income = income_df['amount'].sum() if not income_df.empty else 0
        total_expense = expense_df['amount'].sum() if not expense_df.empty else 0
        card_total = html.Div([
            html.Div([
                html.Div([
                    html.Span("", style={**accent_style_income, "verticalAlign": "middle"}),
                    html.Span("Total Income", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
                html.Div(f"₹{total_income:,.2f}", className="fw-bold text-center", style={"color": "#198754", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
                html.Hr(style={"borderColor": "#eee", "margin": "8px 0", "width": "100%"}),
                html.Div([
                    html.Span("", style={**accent_style_expense, "verticalAlign": "middle"}),
                    html.Span("Total Expense", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px", "marginTop": "4px"}),
                html.Div(f"₹{total_expense:,.2f}", className="fw-bold text-center", style={"color": "#dc3545", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            ], style=CARD_CONTENT_STYLE)
        ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
        profit = total_income - total_expense
        card_profitloss = html.Div([
            html.Div([
                html.Div([
                    html.Span("", style={**accent_style_profit, "verticalAlign": "middle"}),
                    html.Span("Profit / Loss", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
                html.Div(f"₹{profit:,.2f}", className="fw-bold text-center", style={"color": ("#198754" if profit >= 0 else "#dc3545"), "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
                html.Small("(Income - Expense)", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "marginBottom": "8px"}),
            ], style=CARD_CONTENT_STYLE)
        ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
        freq_type = df['transation_type'].mode()[0] if not df.empty else "-"
        freq_count = df['transation_type'].value_counts().max() if not df.empty else 0
        card_frequent = html.Div([
            html.Div([
                html.Div([
                    html.Span("", style={**accent_style_freq, "verticalAlign": "middle"}),
                    html.Span("Most Frequent Type", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
                ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
                html.Div(freq_type.title(), className="fw-bold text-center", style={"color": "#0dcaf0", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
                html.Small(f"{freq_count} times", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
            ], style=CARD_CONTENT_STYLE)
        ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
        
        # Filters
        if transation_type:
            df = df[df['transation_type'].isin(transation_type)]
        if type_filter:
            df = df[df['type'].isin(type_filter)]
        
        # Table
        table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
        )
        
        # Trend Analysis
        df_trend = df.copy()
        df_trend['date'] = pd.to_datetime(df_trend['date'])
        df_trend = df_trend.set_index('date').sort_index()
        trend = df_trend.resample(granularity)['amount'].sum().reset_index()
        trend_fig = px.line(
            trend,
            x='date',
            y='amount',
            title='How Your Total Amount Changes Over Time',
            labels={'date': 'Date', 'amount': 'Total Amount'}
        )
        trend_fig.update_layout(showlegend=False)
        
        # Projection (bar + line combo)
        if len(trend) > 1:
            trend['ordinal_date'] = trend['date'].map(datetime.toordinal)
            X = trend[['ordinal_date']]
            y = trend['amount']
            model = LinearRegression()
            model.fit(X, y)
            freq = granularity
            future_dates = pd.date_range(trend['date'].max(), periods=6, freq=freq)[1:]
            future_ordinals = future_dates.map(datetime.toordinal).values.reshape(-1, 1)
            future_preds = model.predict(future_ordinals)
            projection_fig = go.Figure()
            projection_fig.add_trace(go.Bar(x=trend['date'], y=trend['amount'], name='Actual', marker_color='#198754'))
            projection_fig.add_trace(go.Scatter(x=future_dates, y=future_preds, mode='lines+markers', name='Projection', line=dict(color='#ffc107', dash='solid')))
            projection_fig.update_layout(
                title='Predicted Future Amounts',
                xaxis_title='Date',
                yaxis_title='Predicted Total Amount',
                legend_title_text='Legend',
                barmode='group'
            )
        else:
            projection_fig = go.Figure()
        
        all_data_fig = px.scatter(
            df,
            x='date',
            y='amount',
            color='transation_type',
            symbol='type',
            hover_data=['description'],
            title='All Transactions by Date and Amount',
            labels={'date': 'Date', 'amount': 'Amount', 'transation_type': 'Transaction Type', 'type': 'Recurring/One-time'}
        )
        all_data_fig.update_layout(legend_title_text='Transaction Type')
        
        return [transation_type_options, type_options, False, False, False, False, card_highest_income, card_highest_expense, card_total, card_profitloss, card_frequent, table, trend_fig, projection_fig, all_data_fig, False, False, None]
    # If a file is uploaded, check for duplicates and show modal if needed
    if contents is not None and triggered.startswith('upload-data'):
        df_upload = parse_contents(contents, filename)
        if df_upload is not None and set(['transation_type', 'amount', 'type', 'description', 'date', 'title']).issubset(df_upload.columns):
            df_upload['date'] = pd.to_datetime(df_upload['date'])
            duplicate_rows = insert_transactions(df_upload)
            if duplicate_rows:
                # Show modal with duplicate details
                dup_list = html.Ul([
                    html.Li(', '.join(str(x) for x in row)) for row in duplicate_rows[:10]
                ] + ([html.Li('...and more') if len(duplicate_rows) > 10 else None]))
                return [dash.no_update] * 15 + [False, True, dup_list]
    # Always fetch from DB for display
    df = fetch_transactions(start_date, end_date, transation_type, type_filter)
    if df is None or df.empty:
        return [[], [], True, True, True, True, None, None, None, None, None, html.Div("No data available. Upload a file to get started."), go.Figure(), go.Figure(), go.Figure(), False, False, None]
    df['date'] = pd.to_datetime(df['date'])
    # Prepare filter options
    transation_type_options = [{'label': str(val), 'value': val} for val in sorted(df['transation_type'].dropna().unique())]
    type_options = [{'label': str(val), 'value': val} for val in sorted(df['type'].dropna().unique())]
    # --- Summary Analysis ---
    # Highest Income & Expense
    income_df = df[df['transation_type'] == 'income']
    expense_df = df[df['transation_type'] == 'expense']
    highest_income = income_df['amount'].max() if not income_df.empty else 0
    highest_income_row = income_df.loc[income_df['amount'].idxmax()] if not income_df.empty else None
    highest_expense = expense_df['amount'].max() if not expense_df.empty else 0
    highest_expense_row = expense_df.loc[expense_df['amount'].idxmax()] if not expense_df.empty else None
    # Accent styles for each card
    accent_style_income = {"width": "16px", "height": "16px", "borderRadius": "50%", "background": "#198754", "display": "inline-block", "marginRight": "8px"}
    accent_style_expense = {"width": "16px", "height": "16px", "borderRadius": "50%", "background": "#dc3545", "display": "inline-block", "marginRight": "8px"}
    accent_style_profit = {"width": "32px", "height": "32px", "borderRadius": "50%", "background": "#ffc107", "display": "inline-block", "marginRight": "12px"}
    accent_style_freq = {"width": "32px", "height": "32px", "borderRadius": "50%", "background": "#0dcaf0", "display": "inline-block", "marginRight": "12px"}
    # Highest Income
    card_highest_income = html.Div([
        html.Div([
            html.Div([
                html.Span("", style={**accent_style_income, "verticalAlign": "middle"}),
                html.Span("Highest Income", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
            html.Div(f"₹{highest_income:,.2f}" if highest_income else "-", className="fw-bold text-center", style={"color": "#198754", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            html.Small(highest_income_row['title'] if highest_income_row is not None and 'title' in highest_income_row else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "fontStyle": "italic"}),
            html.Small(highest_income_row['description'] if highest_income_row is not None else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
        ], style=CARD_CONTENT_STYLE)
    ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
    # Highest Expense
    card_highest_expense = html.Div([
        html.Div([
            html.Div([
                html.Span("", style={**accent_style_expense, "verticalAlign": "middle"}),
                html.Span("Highest Expense", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
            html.Div(f"₹{highest_expense:,.2f}" if highest_expense else "-", className="fw-bold text-center", style={"color": "#dc3545", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            html.Small(highest_expense_row['title'] if highest_expense_row is not None and 'title' in highest_expense_row else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "fontStyle": "italic"}),
            html.Small(highest_expense_row['description'] if highest_expense_row is not None else "", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
        ], style=CARD_CONTENT_STYLE)
    ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
    # Total Income & Expense
    total_income = income_df['amount'].sum() if not income_df.empty else 0
    total_expense = expense_df['amount'].sum() if not expense_df.empty else 0
    card_total = html.Div([
        html.Div([
            html.Div([
                html.Span("", style={**accent_style_income, "verticalAlign": "middle"}),
                html.Span("Total Income", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
            html.Div(f"₹{total_income:,.2f}", className="fw-bold text-center", style={"color": "#198754", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            html.Hr(style={"borderColor": "#eee", "margin": "8px 0", "width": "100%"}),
            html.Div([
                html.Span("", style={**accent_style_expense, "verticalAlign": "middle"}),
                html.Span("Total Expense", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px", "marginTop": "4px"}),
            html.Div(f"₹{total_expense:,.2f}", className="fw-bold text-center", style={"color": "#dc3545", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
        ], style=CARD_CONTENT_STYLE)
    ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
    # Profit vs Loss
    profit = total_income - total_expense
    card_profitloss = html.Div([
        html.Div([
            html.Div([
                html.Span("", style={**accent_style_profit, "verticalAlign": "middle"}),
                html.Span("Profit / Loss", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
            html.Div(f"₹{profit:,.2f}", className="fw-bold text-center", style={"color": ("#198754" if profit >= 0 else "#dc3545"), "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            html.Small("(Income - Expense)", className="text-muted text-center w-100", style={"fontSize": "0.75rem", "marginBottom": "8px"}),
        ], style=CARD_CONTENT_STYLE)
    ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
    # Most Frequent Transaction Type
    freq_type = df['transation_type'].mode()[0] if not df.empty else "-"
    freq_count = df['transation_type'].value_counts().max() if not df.empty else 0
    card_frequent = html.Div([
        html.Div([
            html.Div([
                html.Span("", style={**accent_style_freq, "verticalAlign": "middle"}),
                html.Span("Most Frequent Type", className="small text-uppercase text-muted ms-1", style={"verticalAlign": "middle", "fontSize": "0.8rem"}),
            ], className="d-flex align-items-center justify-content-center w-100", style={"marginBottom": "4px"}),
            html.Div(freq_type.title(), className="fw-bold text-center", style={"color": "#0dcaf0", "wordBreak": "break-all", "fontSize": "1.1rem", "marginBottom": "2px"}),
            html.Small(f"{freq_count} times", className="text-muted text-center w-100", style={"fontSize": "0.75rem"}),
        ], style=CARD_CONTENT_STYLE)
    ], style={**SUMMARY_CARD_STYLE, "width": "100%", "height": "100%"})
    # Table
    table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
    )
    # Trend Analysis
    df_trend = df.copy()
    df_trend['date'] = pd.to_datetime(df_trend['date'])
    df_trend = df_trend.set_index('date').sort_index()
    trend = df_trend.resample(granularity)['amount'].sum().reset_index()
    trend_fig = px.line(
        trend,
        x='date',
        y='amount',
        title='How Your Total Amount Changes Over Time',
        labels={'date': 'Date', 'amount': 'Total Amount'}
    )
    trend_fig.update_layout(showlegend=False)
    # Projection (bar + line combo)
    if len(trend) > 1:
        trend['ordinal_date'] = trend['date'].map(datetime.toordinal)
        X = trend[['ordinal_date']]
        y = trend['amount']
        model = LinearRegression()
        model.fit(X, y)
        freq = granularity
        future_dates = pd.date_range(trend['date'].max(), periods=6, freq=freq)[1:]
        future_ordinals = future_dates.map(datetime.toordinal).values.reshape(-1, 1)
        future_preds = model.predict(future_ordinals)
        projection_fig = go.Figure()
        projection_fig.add_trace(go.Bar(x=trend['date'], y=trend['amount'], name='Actual', marker_color='#198754'))
        projection_fig.add_trace(go.Scatter(x=future_dates, y=future_preds, mode='lines+markers', name='Projection', line=dict(color='#ffc107', dash='solid')))
        projection_fig.update_layout(
            title='Predicted Future Amounts',
            xaxis_title='Date',
            yaxis_title='Predicted Total Amount',
            legend_title_text='Legend',
            barmode='group'
        )
    else:
        projection_fig = go.Figure()
    all_data_fig = px.scatter(
        df,
        x='date',
        y='amount',
        color='transation_type',
        symbol='type',
        hover_data=['description'],
        title='All Transactions by Date and Amount',
        labels={'date': 'Date', 'amount': 'Amount', 'transation_type': 'Transaction Type', 'type': 'Recurring/One-time'}
    )
    all_data_fig.update_layout(legend_title_text='Transaction Type')
    return [transation_type_options, type_options, False, False, False, False, card_highest_income, card_highest_expense, card_total, card_profitloss, card_frequent, table, trend_fig, projection_fig, all_data_fig, False, False, None]

@app.callback(
    Output("download-template", "data"),
    Input("btn-download-template", "n_clicks"),
    prevent_initial_call=True
)
def download_template(n_clicks):
    template_df = pd.DataFrame({
        'transation_type': [],
        'amount': [],
        'type': [],
        'description': [],
        'date': [],
        'title': []
    })
    return dcc.send_data_frame(template_df.to_excel, "financial_template.xlsx", index=False)

# Update the pie chart callback to control modal open/close
@app.callback(
    Output('summary-pie', 'figure'),
    Output('summary-pie-modal', 'is_open'),
    [Input('card-highest-income', 'n_clicks'),
     Input('card-highest-expense', 'n_clicks'),
     Input('card-total', 'n_clicks'),
     Input('card-profitloss', 'n_clicks'),
     Input('card-frequent', 'n_clicks'),
     Input('upload-data', 'contents'),
     Input('summary-pie-modal', 'is_open')],
    [State('upload-data', 'filename')]
)
def show_summary_pie(n_income, n_expense, n_total, n_profit, n_freq, contents, is_open, filename):
    import pandas as pd
    ctx = callback_context
    if not ctx.triggered or contents is None:
        return go.Figure(), False
    df = parse_contents(contents, filename)
    if df is None or not set(['transation_type', 'amount', 'type', 'description', 'date', 'title']).issubset(df.columns):
        return go.Figure(), False
    df['date'] = pd.to_datetime(df['date'])
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    # Close modal if backdrop or close button is clicked
    if btn_id == 'summary-pie-modal':
        return go.Figure(), False
    if btn_id == 'card-highest-income':
        pie_df = df[df['transation_type'] == 'income']
        if pie_df.empty:
            return go.Figure(), False
        fig = px.pie(pie_df, names='title', values='amount', title='Income Breakdown by Title')
        return fig, True
    elif btn_id == 'card-highest-expense':
        pie_df = df[df['transation_type'] == 'expense']
        if pie_df.empty:
            return go.Figure(), False
        fig = px.pie(pie_df, names='title', values='amount', title='Expense Breakdown by Title')
        return fig, True
    elif btn_id == 'card-total':
        fig = px.pie(df, names='transation_type', values='amount', title='Transaction Type Breakdown')
        return fig, True
    elif btn_id == 'card-profitloss':
        pie_df = df[df['transation_type'].isin(['income', 'expense'])]
        fig = px.pie(pie_df, names='transation_type', values='amount', title='Income vs Expense')
        return fig, True
    elif btn_id == 'card-frequent':
        fig = px.pie(df, names='transation_type', title='Transaction Type Frequency')
        return fig, True
    return go.Figure(), False

# Email modal callback
@app.callback(
    [Output('modal-email', 'is_open'),
     Output('email-status', 'children')],
    [Input('btn-open-email', 'n_clicks'),
     Input('btn-send-email', 'n_clicks'),
     Input('btn-close-email', 'n_clicks')],
    [State('modal-email', 'is_open'),
     State('smtp-server', 'value'),
     State('smtp-port', 'value'),
     State('sender-email', 'value'),
     State('sender-password', 'value'),
     State('recipient-emails', 'value'),
     State('email-subject', 'value'),
     State('email-body', 'value')],
    prevent_initial_call=True
)
def handle_email_modal(open_clicks, send_clicks, close_clicks, is_open, smtp_server, smtp_port, sender_email, sender_password, recipient_emails, subject, body):
    ctx = callback_context
    if not ctx.triggered:
        return False, ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'btn-open-email':
        return True, ""
    elif button_id == 'btn-close-email':
        return False, ""
    elif button_id == 'btn-send-email':
        # Validate inputs
        if not all([smtp_server, smtp_port, sender_email, sender_password, recipient_emails, subject, body]):
            return True, dbc.Alert("Please fill in all fields", color="danger")
        
        # Parse recipient emails
        email_list = [email.strip() for email in recipient_emails.split('\n') if email.strip()]
        if not email_list:
            return True, dbc.Alert("Please enter at least one recipient email", color="danger")
        
        # Validate email formats
        invalid_emails = [email for email in email_list if not validate_email(email)]
        if invalid_emails:
            return True, dbc.Alert(f"Invalid email format(s): {', '.join(invalid_emails)}", color="danger")
        
        # Send email
        success, message = send_email_notification(
            email_list, subject, body, 
            smtp_server, int(smtp_port), 
            sender_email, sender_password
        )
        
        if success:
            return False, dbc.Alert(message, color="success")
        else:
            return True, dbc.Alert(message, color="danger")
    
    return is_open, ""

if __name__ == '__main__':
    app.run(debug=True) 
server = app.server
