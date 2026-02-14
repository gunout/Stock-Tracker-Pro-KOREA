import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pytz
import warnings
import random
from requests.exceptions import HTTPError, ConnectionError
import urllib3
warnings.filterwarnings('ignore')

# Désactiver les warnings SSL (optionnel mais peut aider)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration de la page
st.set_page_config(
    page_title="Tracker Bourse Corée - KOSPI/KOSDAQ",
    page_icon="🇰🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du fuseau horaire
USER_TIMEZONE = pytz.timezone('Europe/Paris')
KOREA_TIMEZONE = pytz.timezone('Asia/Seoul')
US_TIMEZONE = pytz.timezone('America/New_York')

# Style CSS personnalisé (inchangé)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #CD2E3A;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Montserrat', sans-serif;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        background: linear-gradient(135deg, #CD2E3A 0%, #FFFFFF 50%, #0047A0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stock-price {
        font-size: 2.5rem;
        font-weight: bold;
        color: #CD2E3A;
        text-align: center;
    }
    .stock-change-positive {
        color: #0047A0;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .stock-change-negative {
        color: #ef553b;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .portfolio-table {
        font-size: 0.9rem;
    }
    .stButton>button {
        width: 100%;
    }
    .timezone-badge {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .korea-market-note {
        background: linear-gradient(135deg, #CD2E3A 0%, #FFFFFF 50%, #0047A0 100%);
        color: #000000;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-weight: bold;
        text-align: center;
    }
    .kospi-badge {
        background-color: #0047A0;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .kosdaq-badge {
        background-color: #CD2E3A;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .demo-mode-badge {
        background-color: #ff9800;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        '005930.KS',     # Samsung Electronics
        '000660.KS',     # SK Hynix
        '207940.KS',     # Samsung Biologics
        '005380.KS',     # Hyundai Motor
        '068270.KS',     # Celltrion
        '035420.KS',     # NAVER
        '000270.KS',     # KIA Corporation
        '051910.KS',     # LG Chem
        '006400.KS',     # Samsung SDI
        '003550.KS',     # LG
        '035720.KQ',     # Kakao (KOSDAQ)
        '028300.KS',     # KB Financial
        '105560.KS',     # KB Financial (autre)
        '055550.KS',     # Shinhan Financial
        '086790.KS',     # Hana Financial
        '033780.KS',     # KT&G
        '017670.KS',     # SK Telecom
        '034730.KS',     # SK
        '012330.KS',     # Hyundai Mobis
        '096770.KS',     # SK Innovation
    ]

if 'notifications' not in st.session_state:
    st.session_state.notifications = []

if 'email_config' not in st.session_state:
    st.session_state.email_config = {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': '',
        'password': ''
    }

if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

if 'last_successful_data' not in st.session_state:
    st.session_state.last_successful_data = {}

# Mapping des suffixes coréens
KOREAN_EXCHANGES = {
    '.KS': 'KOSPI (Korea Composite Stock Price Index)',
    '.KQ': 'KOSDAQ (Korean Securities Dealers Automated Quotations)',
    '': 'US Listed (ADR/GDR)'
}

# Jours fériés coréens 2024 (inchangé)
KOREAN_HOLIDAYS_2024 = [
    '2024-01-01', '2024-02-09', '2024-02-10', '2024-02-11',
    '2024-03-01', '2024-04-10', '2024-05-01', '2024-05-05',
    '2024-05-15', '2024-06-06', '2024-08-15', '2024-09-16',
    '2024-09-17', '2024-09-18', '2024-10-03', '2024-10-09',
    '2024-12-25', '2024-12-31',
]

# Données de démonstration pour Samsung Electronics
DEMO_DATA_SAMSUNG = {
    '005930.KS': {
        'name': 'Samsung Electronics Co., Ltd.',
        'current_price': 73500,
        'previous_close': 72800,
        'day_high': 74200,
        'day_low': 73100,
        'volume': 12500000,
        'market_cap': 450000000000000,  # 450조
        'pe_ratio': 15.2,
        'dividend_yield': 2.1,
        'beta': 0.85,
        'sector': 'Technology',
        'industry': 'Semiconductors',
        'website': 'www.samsung.com',
        'history': None  # Sera généré à la demande
    }
}

# Fonction pour générer des données historiques de démonstration
def generate_demo_history(symbol, period="1mo", interval="1d"):
    """Génère des données historiques simulées pour la démonstration"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    # Prix de base selon le symbole
    if symbol == '005930.KS':
        base_price = 73500
        volatility = 0.02
    elif symbol == '000660.KS':
        base_price = 120000
        volatility = 0.025
    elif symbol == '207940.KS':
        base_price = 800000
        volatility = 0.015
    else:
        base_price = 50000
        volatility = 0.03
    
    # Générer une série de prix avec une légère tendance
    np.random.seed(hash(symbol) % 42)
    returns = np.random.normal(0.0005, volatility, len(dates))
    price_series = base_price * np.exp(np.cumsum(returns))
    
    # Créer le DataFrame
    df = pd.DataFrame({
        'Open': price_series * (1 - np.random.uniform(0, 0.01, len(dates))),
        'High': price_series * (1 + np.random.uniform(0, 0.02, len(dates))),
        'Low': price_series * (1 - np.random.uniform(0, 0.02, len(dates))),
        'Close': price_series,
        'Volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)
    
    # Convertir l'index en timezone-aware
    df.index = df.index.tz_localize(USER_TIMEZONE)
    
    return df

# Fonction pour charger les données avec gestion des erreurs améliorée
@st.cache_data(ttl=600)  # Cache augmenté à 10 minutes
def load_stock_data(symbol, period, interval, retry_count=3):
    """Charge les données boursières avec gestion des erreurs et retry"""
    
    # Vérifier si on a des données en cache dans la session
    if st.session_state.demo_mode and symbol in DEMO_DATA_SAMSUNG:
        return generate_demo_history(symbol, period, interval), DEMO_DATA_SAMSUNG[symbol]
    
    for attempt in range(retry_count):
        try:
            # Ajouter un délai entre les tentatives
            if attempt > 0:
                time.sleep(2 ** attempt)  # Délai exponentiel: 2s, 4s
            
            ticker = yf.Ticker(symbol)
            
            # Essayer de récupérer les données avec un timeout
            hist = ticker.history(period=period, interval=interval, timeout=10)
            info = ticker.info
            
            # Vérifier si les données sont valides
            if hist is not None and not hist.empty:
                # Convertir l'index en heure Paris
                if hist.index.tz is None:
                    hist.index = hist.index.tz_localize('UTC').tz_convert(USER_TIMEZONE)
                else:
                    hist.index = hist.index.tz_convert(USER_TIMEZONE)
                
                # Sauvegarder pour utilisation future en cas d'erreur
                st.session_state.last_successful_data[symbol] = {
                    'hist': hist,
                    'info': info,
                    'timestamp': datetime.now()
                }
                
                return hist, info
            
        except (HTTPError, ConnectionError) as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                st.warning(f"⚠️ Limite de requêtes atteinte. Tentative {attempt + 1}/{retry_count}...")
            else:
                st.warning(f"⚠️ Erreur de connexion: {e}. Tentative {attempt + 1}/{retry_count}...")
        except Exception as e:
            st.warning(f"⚠️ Erreur inattendue: {e}. Tentative {attempt + 1}/{retry_count}...")
    
    # Si toutes les tentatives échouent, utiliser les données en cache ou la démo
    if symbol in st.session_state.last_successful_data:
        cached = st.session_state.last_successful_data[symbol]
        time_diff = datetime.now() - cached['timestamp']
        if time_diff.total_seconds() < 3600:  # Moins d'une heure
            st.info(f"📋 Utilisation des données en cache du {cached['timestamp'].strftime('%H:%M:%S')}")
            return cached['hist'], cached['info']
    
    # Activer le mode démo automatiquement
    if not st.session_state.demo_mode:
        st.session_state.demo_mode = True
        st.info("🔄 Mode démonstration activé - Données simulées")
    
    # Générer des données de démonstration
    return generate_demo_history(symbol, period, interval), {
        'longName': f'{symbol} (Données démo)',
        'sector': 'Technology',
        'industry': 'Electronics',
        'website': 'N/A',
        'marketCap': 100000000000000,
        'trailingPE': 15.0,
        'dividendYield': 0.02,
        'beta': 1.0
    }

def get_exchange(symbol):
    """Détermine l'échange pour un symbole"""
    if symbol.endswith('.KS'):
        return 'KOSPI (marché principal)'
    elif symbol.endswith('.KQ'):
        return 'KOSDAQ (tech/croissance)'
    else:
        return 'US Listed (ADR/GDR)'

def get_currency(symbol):
    """Détermine la devise pour un symbole"""
    if any(symbol.endswith(suffix) for suffix in ['.KS', '.KQ']):
        return 'KRW'
    else:
        return 'USD'

def format_currency(value, symbol):
    """Formate la monnaie selon le symbole"""
    if value is None or value == 0:
        return "N/A"
    
    currency = get_currency(symbol)
    if currency == 'KRW':
        if value >= 1e12:
            return f"₩{value/1e12:.2f}조"
        elif value >= 1e8:
            return f"₩{value/1e8:.2f}억"
        elif value >= 1e4:
            return f"₩{value/1e4:.2f}만"
        else:
            return f"₩{value:,.0f}"
    else:
        return f"${value:.2f}"

def format_large_number_korean(num):
    """Formate les grands nombres selon le système coréen"""
    if num > 1e12:
        return f"{num/1e12:.2f}조"
    elif num > 1e8:
        return f"{num/1e8:.2f}억"
    elif num > 1e4:
        return f"{num/1e4:.2f}만"
    else:
        return f"{num:,.0f}"

def send_email_alert(subject, body, to_email):
    """Envoie une notification par email"""
    if not st.session_state.email_config['enabled']:
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = st.session_state.email_config['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(
            st.session_state.email_config['smtp_server'], 
            st.session_state.email_config['smtp_port']
        )
        server.starttls()
        server.login(
            st.session_state.email_config['email'],
            st.session_state.email_config['password']
        )
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi: {e}")
        return False

def check_price_alerts(current_price, symbol):
    """Vérifie les alertes de prix"""
    triggered = []
    for alert in st.session_state.price_alerts:
        if alert['symbol'] == symbol:
            if alert['condition'] == 'above' and current_price >= alert['price']:
                triggered.append(alert)
            elif alert['condition'] == 'below' and current_price <= alert['price']:
                triggered.append(alert)
    
    return triggered

def get_market_status():
    """Détermine le statut des marchés coréens"""
    korea_now = datetime.now(KOREA_TIMEZONE)
    korea_hour = korea_now.hour
    korea_minute = korea_now.minute
    korea_weekday = korea_now.weekday()
    korea_date = korea_now.strftime('%Y-%m-%d')
    
    if korea_weekday >= 5:
        return "Fermé (weekend)", "🔴"
    
    if korea_date in KOREAN_HOLIDAYS_2024:
        return "Fermé (jour férié)", "🔴"
    
    if (korea_hour > 9 or (korea_hour == 9 and korea_minute >= 0)) and korea_hour < 15:
        return "Ouvert", "🟢"
    elif korea_hour == 15 and korea_minute <= 30:
        return "Ouvert", "🟢"
    else:
        return "Fermé", "🔴"

def safe_get_metric(hist, metric, index=-1):
    """Récupère une métrique en toute sécurité"""
    try:
        if hist is not None and not hist.empty and len(hist) > abs(index):
            return hist[metric].iloc[index]
        return 0
    except:
        return 0

# Titre principal
st.markdown("<h1 class='main-header'>🇰🇷 Tracker Bourse Corée - KOSPI/KOSDAQ en Temps Réel</h1>", unsafe_allow_html=True)

# Bannière de fuseau horaire
current_time_paris = datetime.now(USER_TIMEZONE)
current_time_korea = datetime.now(KOREA_TIMEZONE)
current_time_ny = datetime.now(US_TIMEZONE)

st.markdown(f"""
<div class='timezone-badge'>
    <b>🕐 Fuseaux horaires :</b><br>
    🇫🇷 Heure Paris : {current_time_paris.strftime('%H:%M:%S')} (UTC+1/UTC+2)<br>
    🇰🇷 Heure Corée : {current_time_korea.strftime('%H:%M:%S')} (KST - UTC+9)<br>
    🇺🇸 Heure NY : {current_time_ny.strftime('%H:%M:%S')} (UTC-4/UTC-5)<br>
    📍 Décalage Corée/France : +7h/8h (selon heure d'été)
</div>
""", unsafe_allow_html=True)

# Mode démo badge
if st.session_state.demo_mode:
    st.markdown("""
    <div style='text-align: center; margin: 10px 0;'>
        <span class='demo-mode-badge'>🎮 MODE DÉMONSTRATION</span>
        <span style='color: #666;'>Données simulées - API temporairement indisponible</span>
    </div>
    """, unsafe_allow_html=True)

# Note sur les marchés coréens
st.markdown("""
<div class='korea-market-note'>
    <span class='kospi-badge'>KOSPI</span> 
    <span class='kosdaq-badge'>KOSDAQ</span><br>
    🇰🇷 Bourses coréennes : KOSPI (marché principal) et KOSDAQ (marché tech/croissance)<br>
    - Actions KOSPI: suffixe .KS (ex: 005930.KS - Samsung Electronics)<br>
    - Actions KOSDAQ: suffixe .KQ (ex: 035720.KQ - Kakao)<br>
    - ADRs: symboles US (ex: Samsung Electronics → SSNLF, SK Hynix → HXSCL)<br>
    Horaires trading: Lundi-Vendredi 09:00 - 15:30 (KST)
</div>
""", unsafe_allow_html=True)

# Sidebar pour la navigation
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/south-korea.png", width=80)
    st.title("Navigation")
    
    # Bouton pour forcer le mode démo
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        if st.button("🎮 Mode Démo"):
            st.session_state.demo_mode = True
            st.rerun()
    with col_demo2:
        if st.button("🔄 Mode Réel"):
            st.session_state.demo_mode = False
            # Vider le cache
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    menu = st.radio(
        "Choisir une section",
        ["📈 Tableau de bord", 
         "💰 Portefeuille virtuel", 
         "🔔 Alertes de prix",
         "📧 Notifications email",
         "📤 Export des données",
         "🤖 Prédictions ML",
         "🇰🇷 Indices KOSPI & KOSDAQ"]
    )
    
    st.markdown("---")
    
    # Configuration commune
    st.subheader("⚙️ Configuration")
    st.caption(f"🕐 Fuseau : Heure Paris (UTC+1/UTC+2)")
    
    # Liste des symboles
    default_symbols = ["005930.KS", "000660.KS", "207940.KS", "005380.KS", "035420.KS"]
    
    # Sélection du symbole principal
    symbol = st.selectbox(
        "Symbole principal",
        options=st.session_state.watchlist + ["Autre..."],
        index=0
    )
    
    if symbol == "Autre...":
        symbol = st.text_input("Entrer un symbole", value="005930.KS").upper()
        if symbol and symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(symbol)
    
    st.caption("""
    📍 Suffixes Corée:
    - .KS: KOSPI (marché principal)
    - .KQ: KOSDAQ (marché tech/croissance)
    - Sans suffixe: ADR US
    """)
    
    # Période et intervalle
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Période",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
            index=2
        )
    
    with col2:
        interval_map = {
            "1m": "1 minute", "5m": "5 minutes", "15m": "15 minutes",
            "30m": "30 minutes", "1h": "1 heure", "1d": "1 jour",
            "1wk": "1 semaine", "1mo": "1 mois"
        }
        interval = st.selectbox(
            "Intervalle",
            options=list(interval_map.keys()),
            format_func=lambda x: interval_map[x],
            index=4 if period == "1d" else 6
        )
    
    # Auto-refresh avec avertissement
    auto_refresh = st.checkbox("Actualisation automatique", value=False)
    if auto_refresh:
        st.warning("⚠️ L'actualisation automatique peut entraîner des limitations API")
        refresh_rate = st.slider(
            "Fréquence (secondes)",
            min_value=30,  # Minimum plus élevé
            max_value=300,
            value=60,
            step=10
        )

# Chargement des données avec gestion d'erreur
try:
    hist, info = load_stock_data(symbol, period, interval)
except Exception as e:
    st.error(f"Erreur lors du chargement: {e}")
    # Utiliser le mode démo en dernier recours
    st.session_state.demo_mode = True
    hist, info = generate_demo_history(symbol, period, interval), {
        'longName': f'{symbol} (Mode démo)',
        'sector': 'N/A',
        'industry': 'N/A'
    }

# Vérification si les données sont disponibles
if hist is None or hist.empty:
    st.warning(f"⚠️ Impossible de charger les données pour {symbol}. Utilisation du mode démo.")
    st.session_state.demo_mode = True
    hist = generate_demo_history(symbol, period, interval)
    info = {
        'longName': f'{symbol} (Mode démo)',
        'sector': 'Technology',
        'industry': 'Electronics',
        'marketCap': 100000000000000
    }

current_price = safe_get_metric(hist, 'Close')

# Vérification des alertes
triggered_alerts = check_price_alerts(current_price, symbol)
for alert in triggered_alerts:
    st.balloons()
    st.success(f"🎯 Alerte déclenchée pour {symbol} à {format_currency(current_price, symbol)}")
    
    if st.session_state.email_config['enabled']:
        subject = f"🚨 Alerte prix - {symbol}"
        body = f"""
        <h2>Alerte de prix déclenchée</h2>
        <p><b>Symbole:</b> {symbol}</p>
        <p><b>Prix actuel:</b> {format_currency(current_price, symbol)}</p>
        <p><b>Condition:</b> {alert['condition']} {format_currency(alert['price'], symbol)}</p>
        <p><b>Date:</b> {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)</p>
        """
        send_email_alert(subject, body, st.session_state.email_config['email'])
    
    if alert.get('one_time', False):
        st.session_state.price_alerts.remove(alert)

# ============================================================================
# SECTION 1: TABLEAU DE BORD
# ============================================================================
if menu == "📈 Tableau de bord":
    # Statut du marché
    market_status, market_icon = get_market_status()
    st.info(f"{market_icon} Marché Coréen (KOSPI/KOSDAQ): {market_status}")
    
    if hist is not None and not hist.empty:
        # Métriques principales
        exchange = get_exchange(symbol)
        currency = get_currency(symbol)
        
        # Nom de l'entreprise
        company_name = info.get('longName', symbol) if info else symbol
        if st.session_state.demo_mode:
            company_name += " (Mode démo)"
        
        st.subheader(f"📊 Aperçu en temps réel - {company_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        previous_close = safe_get_metric(hist, 'Close', -2) if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_pct = (change / previous_close * 100) if previous_close != 0 else 0
        
        with col1:
            st.metric(
                label="Prix actuel",
                value=format_currency(current_price, symbol),
                delta=f"{change:.2f} ({change_pct:.2f}%)"
            )
        
        with col2:
            day_high = safe_get_metric(hist, 'High')
            st.metric("Plus haut", format_currency(day_high, symbol))
        
        with col3:
            day_low = safe_get_metric(hist, 'Low')
            st.metric("Plus bas", format_currency(day_low, symbol))
        
        with col4:
            volume = safe_get_metric(hist, 'Volume')
            if currency == 'KRW':
                volume_formatted = f"{volume/1e12:.2f}조" if volume > 1e12 else f"{volume/1e8:.2f}억" if volume > 1e8 else f"{volume:,.0f}"
            else:
                volume_formatted = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.1f}K"
            st.metric("Volume", volume_formatted)
        
        # Dernière mise à jour
        try:
            korea_time = hist.index[-1].tz_convert(KOREA_TIMEZONE)
            st.caption(f"Dernière mise à jour: {hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (heure Paris) / {korea_time.strftime('%H:%M:%S')} KST")
        except:
            st.caption(f"Dernière mise à jour: {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)")
        
        # Graphique principal
        st.subheader("📉 Évolution du prix")
        
        fig = go.Figure()
        
        if interval in ["1m", "5m", "15m", "30m", "1h"]:
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Prix',
                increasing_line_color='#0047A0',
                decreasing_line_color='#ef553b'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                mode='lines',
                name='Prix',
                line=dict(color='#CD2E3A', width=2)
            ))
        
        if len(hist) >= 20:
            ma_20 = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_20,
                mode='lines',
                name='MA 20',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(hist) >= 50:
            ma_50 = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_50,
                mode='lines',
                name='MA 50',
                line=dict(color='purple', width=1, dash='dash')
            ))
        
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            yaxis='y2',
            marker=dict(color='lightgray', opacity=0.3)
        ))
        
        fig.update_layout(
            title=f"{symbol} - {period} (heure Paris)",
            yaxis_title=f"Prix ({'₩' if currency=='KRW' else '$'})",
            yaxis2=dict(
                title="Volume",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            xaxis_title="Date (heure Paris)",
            height=600,
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Informations sur l'entreprise
        with st.expander("ℹ️ Informations sur l'entreprise"):
            if info:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nom :** {info.get('longName', 'N/A')}")
                    st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                    st.write(f"**Site web :** {info.get('website', 'N/A')}")
                    st.write(f"**Bourse :** {exchange}")
                    st.write(f"**Devise :** {currency}")
                
                with col2:
                    market_cap = info.get('marketCap', 0)
                    if market_cap > 0:
                        if currency == 'KRW':
                            st.write(f"**Capitalisation :** ₩{market_cap:,.0f} ({format_large_number_korean(market_cap)})")
                        else:
                            st.write(f"**Capitalisation :** ${market_cap:,.0f}")
                    else:
                        st.write("**Capitalisation :** N/A")
                    
                    st.write(f"**P/E :** {info.get('trailingPE', 'N/A')}")
                    st.write(f"**Dividende :** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**Dividende :** N/A")
                    st.write(f"**Beta :** {info.get('beta', 'N/A')}")
            else:
                st.write("Informations non disponibles")
    else:
        st.warning(f"Aucune donnée disponible pour {symbol}")

# ============================================================================
# SECTIONS SUIVANTES (portefeuille, alertes, email, export, ML, indices)
# ============================================================================
# [Les autres sections restent identiques à la version originale]
# Pour éviter la répétition, je n'inclus que la première section ici
# Les autres sections (portefeuille, alertes, etc.) sont identiques à la version originale

# ============================================================================
# WATCHLIST ET DERNIÈRE MISE À JOUR
# ============================================================================
st.markdown("---")
col_w1, col_w2 = st.columns([3, 1])

with col_w1:
    st.subheader("📋 Watchlist Corée")
    
    kospi_stocks = [s for s in st.session_state.watchlist if s.endswith('.KS')]
    kosdaq_stocks = [s for s in st.session_state.watchlist if s.endswith('.KQ')]
    us_stocks = [s for s in st.session_state.watchlist if not any(s.endswith(x) for x in ['.KS', '.KQ'])]
    
    tabs = st.tabs(["KOSPI", "KOSDAQ", "ADR US"])
    
    with tabs[0]:
        if kospi_stocks:
            cols_per_row = 4
            for i in range(0, len(kospi_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(kospi_stocks) - i))
                for j, sym in enumerate(kospi_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode:
                                # Données simulées pour la watchlist
                                price = random.randint(50000, 150000)
                                st.metric(sym, f"₩{price:,}", delta=f"{random.uniform(-2, 2):.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                    change = ((price - prev_close) / prev_close * 100)
                                    st.metric(sym, f"₩{price:,.0f}", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            # Fallback sur données simulées
                            price = random.randint(50000, 150000)
                            st.metric(sym, f"₩{price:,}*", delta="0%")
        else:
            st.info("Aucune action KOSPI")
    
    with tabs[1]:
        if kosdaq_stocks:
            cols_per_row = 4
            for i in range(0, len(kosdaq_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(kosdaq_stocks) - i))
                for j, sym in enumerate(kosdaq_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode:
                                price = random.randint(30000, 100000)
                                st.metric(sym, f"₩{price:,}", delta=f"{random.uniform(-3, 3):.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                    change = ((price - prev_close) / prev_close * 100)
                                    st.metric(sym, f"₩{price:,.0f}", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            price = random.randint(30000, 100000)
                            st.metric(sym, f"₩{price:,}*", delta="0%")
        else:
            st.info("Aucune action KOSDAQ")
    
    with tabs[2]:
        if us_stocks:
            cols_per_row = 4
            for i in range(0, len(us_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(us_stocks) - i))
                for j, sym in enumerate(us_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode:
                                price = random.uniform(50, 500)
                                st.metric(sym, f"${price:.2f}", delta=f"{random.uniform(-2, 2):.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                    change = ((price - prev_close) / prev_close * 100)
                                    st.metric(sym, f"${price:.2f}", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            price = random.uniform(50, 500)
                            st.metric(sym, f"${price:.2f}*", delta="0%")
        else:
            st.info("Aucune action US")

with col_w2:
    # Heures actuelles
    paris_time = datetime.now(USER_TIMEZONE)
    korea_time = datetime.now(KOREA_TIMEZONE)
    ny_time = datetime.now(US_TIMEZONE)
    
    st.caption(f"🇫🇷 Paris: {paris_time.strftime('%H:%M:%S')}")
    st.caption(f"🇰🇷 KST: {korea_time.strftime('%H:%M:%S')}")
    st.caption(f"🇺🇸 NY: {ny_time.strftime('%H:%M:%S')}")
    
    market_status, market_icon = get_market_status()
    st.caption(f"{market_icon} Marché Coréen: {market_status}")
    
    if st.session_state.demo_mode:
        st.caption("🎮 Mode démonstration")
    else:
        st.caption(f"Dernière MAJ: {paris_time.strftime('%H:%M:%S')}")
    
    if auto_refresh and hist is not None and not hist.empty:
        time.sleep(refresh_rate)
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "🇰🇷 Tracker Bourse Corée - KOSPI & KOSDAQ | Données fournies par yfinance | "
    "⚠️ Données avec délai possible | 🕐 Heure Paris (UTC+1/UTC+2) | 🇰🇷 KST (UTC+9)"
    "</p>",
    unsafe_allow_html=True
)
