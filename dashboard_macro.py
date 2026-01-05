import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macro Dashboard Pro", layout="centered", page_icon="📈")

# Estilos CSS para limpiar la interfaz
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- 1. GESTIÓN DE CLAVE API (INTELIGENTE) ---
try:
    # Intenta coger la clave de los secretos de Streamlit (Nube)
    FRED_API_KEY = st.secrets["FRED_KEY"]
except:
    # Si falla (estás en local y no tienes secrets.toml), usa esta variable:
    # ⚠️ PEGA TU CLAVE AQUÍ SI ESTÁS EN TU ORDENADOR Y TE DA ERROR
    FRED_API_KEY = 'PON_AQUI_TU_CLAVE_LARGA_DE_FRED'

# --- 2. FUNCIONES DE DATOS ---

def obtener_datos_macro(api_key):
    """Obtiene M2 y FCI de la FED."""
    datos = {}
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    try:
        fred = Fred(api_key=api_key)
        m2 = fred.get_series('M2SL', observation_start=start_date)
        fci = fred.get_series('NFCI', observation_start=start_date)
        
        datos['m2_serie'] = m2
        datos['fci_serie'] = fci
        datos['m2_actual'] = m2.iloc[-1]
        datos['m2_previo'] =