import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA (MODO PRO) ---
st.set_page_config(page_title="Macro Dashboard Pro", layout="centered", page_icon="📈")

# Estilos CSS para ocultar menús y limpiar la interfaz
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- 1. CLAVE API ---
# ⚠️ PEGA TU CLAVE AQUÍ ABAJO
FRED_API_KEY = st.secrets["FRED_KEY"] 

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
        datos['m2_previo'] = m2.iloc[-2]
        datos['fci_actual'] = fci.iloc[-1]
        datos['api_activa'] = True
        
    except Exception as e:
        # Datos simulados de respaldo
        fechas = pd.date_range(start='2023-01-01', periods=24, freq='M')
        datos['m2_serie'] = pd.Series([20000 + i*50 for i in range(24)], index=fechas)
        datos['fci_serie'] = pd.Series([-0.5 + i*0.01 for i in range(24)], index=fechas)
        datos['m2_actual'] = 21000 
        datos['m2_previo'] = 20800
        datos['fci_actual'] = -0.5
        datos['api_activa'] = False
        
    return datos

def obtener_precios_mercado():
    """Obtiene Nasdaq, BTC, Oro y Dólar."""
    tickers = {
        'NASDAQ': '^IXIC',
        'BITCOIN': 'BTC-USD',
        'GOLD': 'GC=F',
        'DXY': 'DX-Y.NYB'
    }
    precios = {}
    historicos = {}
    
    for nombre, simbolo in tickers.items():
        try:
            ticker = yf.Ticker(simbolo)
            hist = ticker.history(period="1y")
            precios[nombre] = hist['Close'].iloc[-1]
            historicos[nombre] = hist['Close']
        except:
            precios[nombre] = 0
            historicos[nombre] = pd.Series([])
            
    return precios, historicos

# --- 3. LÓGICA DE NEGOCIO ---

def analizar_macro(m2_now, m2_prev, fci):
    # Tendencia M2
    trend_m2 = "Subiendo" if m2_now > m2_prev else "Bajando"
    senal_m2 = "🟢 Reflación" if trend_m2 == "Subiendo" else "🔴 Desinflación"
    
    # Estado FCI
    estado_fci = "Relajadas" if fci < 0 else "Restrictivas"
    
    return trend_m2, senal_m2, estado_fci

def generar_pronostico(trend_m2, estado_fci, ism_manuf):
    p = {}
    
    # NASDAQ
    p['nasdaq'] = "↗️ Alcista" if "Subiendo" in trend_m2 else "➡️ Lateral"
    if ism_manuf < 50: p['nasdaq'] += " (⚠️ Riesgo ISM)"
    
    # BITCOIN
    p['btc'] = "🚀 Muy Alcista" if ("Subiendo" in trend_m2 and "Relajadas" in estado_fci) else "🔁 Volátil"
    
    # ORO
    p['gold'] = "↗️ Alcista (Reserva valor)" if "Subiendo" in trend_m2 else "➡️ Neutral"
    
    # DÓLAR
    p['dxy'] = "↘️ Bajista (Debilidad)" if "Relajadas" in estado_fci else "↗️ Alcista (Fortaleza)"
    
    return p

# --- 4. INTERFAZ VISUAL ---

def main():
    st.title("🏛️ VISIÓN MACRO GLOBAL")
    st.caption("Tracking en tiempo real: Liquidez vs Activos")
    
    # Carga de datos
    macro = obtener_datos_macro(FRED_API_KEY)
    precios, historia = obtener_precios_mercado()
    
    # Barra lateral (AHORA CON EL ISM SERVICIOS RECUPERADO)
    with st.sidebar:
        st.header("⚙️ Ajustes")
        ism_manuf = st.number_input("ISM Manufacturero", 48.2)
        ism_serv = st.number_input("ISM Servicios", 52.6) # <--- ¡Aquí está de vuelta!
        st.markdown("---")
        st.caption("Datos: FRED St. Louis & Yahoo Finance")

    # Lógica
    trend_m2, senal_m2, estado_fci = analizar_macro(macro['m2_actual'], macro['m2_previo'], macro['fci_actual'])
    forecast = generar_pronostico(trend_m2, estado_fci, ism_manuf)

    # --- DASHBOARD SUPERIOR (MACRO) ---
    # Ahora usamos 4 columnas para que quepan todos los indicadores
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Liquidez M2", f"{trend_m2}", delta=senal_m2, delta_color="off")
    with col2:
        st.metric("Condic. FCI", f"{macro['fci_actual']:.2f}", delta="< 0 es Bueno", delta_color="inverse")
    with col3:
        st.metric("ISM Manuf.", f"{ism_manuf}", delta="Expansión > 50")
    with col4:
        st.metric("ISM Serv.", f"{ism_serv}", delta="Sostiene Eco") # <--- Nuevo indicador visual

    # Acordeón para gráficos Macro
    with st.expander("📉 Ver Gráficos Macro (M2 y FCI)"):
        st.caption("Liquidez Global (M2)")
        st.line_chart(macro['m2_serie'])
        st.caption("Estrés Financiero (FCI)")
        st.line_chart(macro['fci_serie'])

    st.markdown("---")
    
    # --- DASHBOARD INFERIOR (ACTIVOS) ---
    st.subheader("Mercados & Impacto")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💻 NASDAQ", "₿ BITCOIN", "🥇 ORO", "💵 DÓLAR"])

    def mostrar_activo(nombre, ticker_key, forecast_key, color_grafico):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Precio", f"${precios[ticker_key]:,.2f}")
            st.info(f"Proyección: {forecast[forecast_key]}")
        with c2:
            st.line_chart(historia[ticker_key], color=color_grafico)

    with tab1:
        mostrar_activo("NASDAQ", "NASDAQ", "nasdaq", "#0000FF") 
    with tab2:
        mostrar_activo("BITCOIN", "BITCOIN", "btc", "#FF9900")  
    with tab3:
        mostrar_activo("ORO", "GOLD", "gold", "#FFD700")       
    with tab4:
        mostrar_activo("DÓLAR DXY", "DXY", "dxy", "#008000")    

if __name__ == "__main__":
    main()