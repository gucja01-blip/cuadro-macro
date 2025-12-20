import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cuadro de Mando Macro", layout="centered")

# --- 1. CONFIGURACIÓN DE API (Pon tu clave aquí) ---
# Tienes que pedir tu clave gratuita en: https://fred.stlouisfed.org/apikeys
# Si no tienes clave, el código usará datos simulados para que veas el ejemplo.
FRED_API_KEY = '4d80754d7562963786ce89113fd95e9e' 

# --- 2. FUNCIONES DE EXTRACCIÓN DE DATOS ---

def obtener_datos_macro(api_key):
    """
    Obtiene datos de la Reserva Federal (FRED).
    """
    datos = {}
    try:
        fred = Fred(api_key=api_key)
        
        # M2SL: M2 Money Stock (Liquidez EE.UU. como proxy global)
        m2 = fred.get_series('M2SL', observation_start='2023-01-01')
        
        # NFCI: National Financial Conditions Index (Chicago Fed)
        # Valores negativos = condiciones relajadas
        fci = fred.get_series('NFCI', observation_start='2023-01-01')
        
        datos['m2_actual'] = m2.iloc[-1]
        datos['m2_previo'] = m2.iloc[-2]
        datos['fci_actual'] = fci.iloc[-1]
        datos['api_activa'] = True
        
    except Exception as e:
        # Si falla la API o no hay clave, usamos datos de ejemplo
        st.warning(f"⚠️ Usando datos simulados (Error API: {e})")
        datos['m2_actual'] = 21000 # Billones simulados
        datos['m2_previo'] = 20800
        datos['fci_actual'] = -0.5 # Negativo es bueno/relajado
        datos['api_activa'] = False
        
    return datos

def obtener_precios_mercado():
    """
    Obtiene precios actuales de Nasdaq y Bitcoin usando Yahoo Finance.
    """
    tickers = {
        'NASDAQ': '^IXIC',
        'BITCOIN': 'BTC-USD'
    }
    precios = {}
    for nombre, simbolo in tickers.items():
        ticker = yf.Ticker(simbolo)
        hist = ticker.history(period="5d")
        precios[nombre] = hist['Close'].iloc[-1]
    return precios

# --- 3. LÓGICA DE NEGOCIO (EL CEREBRO DEL SISTEMA) ---

def analizar_liquidez(m2_actual, m2_previo):
    """Determina la tendencia de la liquidez."""
    if m2_actual > m2_previo:
        return "↗️ Subiendo", "Reflación (Liquidez al alza)", "🟢 Bullish"
    else:
        return "↘️ Bajando", "Desinflación (Liquidez a la baja)", "🔴 Bearish"

def analizar_fci(fci_nivel):
    """Determina el estado de las condiciones financieras."""
    if fci_nivel < 0:
        return "Relajadas (Dinero barato)", "🟢 Semáforo Verde"
    else:
        return "Restrictivas (Dinero caro)", "🔴 Semáforo Rojo"

def generar_pronostico(tendencia_m2, estado_fci, ism_manuf):
    """
    Genera el impacto a 3 y 6 meses basado en tus reglas.
    """
    pronostico = {
        'nasdaq_3m': '', 'nasdaq_6m': '',
        'btc_3m': '', 'btc_6m': ''
    }
    
    # Lógica para NASDAQ
    if "Subiendo" in tendencia_m2:
        pronostico['nasdaq_3m'] = "↗️ Alcista (Liquidez busca rendimiento)"
    else:
        pronostico['nasdaq_3m'] = "➡️ Lateral/Bajista"
        
    if ism_manuf < 50:
        pronostico['nasdaq_6m'] = "⚠️ Riesgo de Recesión (ISM < 50)"
    else:
        pronostico['nasdaq_6m'] = "↗️ Alcista Sólido"

    # Lógica para BITCOIN
    if "Subiendo" in tendencia_m2 and "Relajadas" in estado_fci:
        pronostico['btc_3m'] = "🚀 Muy Alcista (Canario en la mina)"
        pronostico['btc_6m'] = "↗️ Alcista (Mientras FCI siga relajado)"
    else:
        pronostico['btc_3m'] = "🔁 Volátil"
        pronostico['btc_6m'] = "⚠️ Precaución"
        
    return pronostico

# --- 4. INTERFAZ DE USUARIO (LO QUE SE VE EN LA WEB) ---

def main():
    st.title("📱 CUADRO DE MANDO MACRO")
    st.markdown("---")

    # 1. Obtener Datos
    macro_data = obtener_datos_macro(FRED_API_KEY)
    market_data = obtener_precios_mercado()
    
    # 2. Inputs Manuales (Ya que el ISM es dato propietario difícil de automatizar gratis)
    st.sidebar.header("Ajustes Manuales")
    ism_manuf = st.sidebar.number_input("ISM Manufacturero (Dato actual)", value=48.2)
    ism_serv = st.sidebar.number_input("ISM Servicios (Dato actual)", value=52.6)

    # 3. Procesar Lógica
    tendencia_m2_txt, estado_macro, senal_m2 = analizar_liquidez(macro_data['m2_actual'], macro_data['m2_previo'])
    estado_fci_txt, senal_fci = analizar_fci(macro_data['fci_actual'])
    forecast = generar_pronostico(tendencia_m2_txt, estado_fci_txt, ism_manuf)

    # --- MOSTRAR DATOS EN PANTALLA ---

    # Cabecera de Estado
    st.info(f"**Estado General:** {estado_macro}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. EL COMBUSTIBLE 🚰")
        st.markdown(f"**Liquidez Global (Proxy M2)**")
        st.write(f"Tendencia: {tendencia_m2_txt}")
        st.write(f"Señal: {senal_m2}")
        
        st.markdown(f"**Condiciones Financieras (FCI)**")
        st.write(f"Estado: {estado_fci_txt}")
        st.write(f"Nivel: {macro_data['fci_actual']:.2f}")
        st.write(f"Señal: {senal_fci}")

    with col2:
        st.subheader("2. EL TERMÓMETRO 🌡️")
        st.markdown(f"**ISM Manufacturero**")
        st.write(f"Dato: {ism_manuf}")
        if ism_manuf < 50:
            st.write("Lectura: ⚠️ Contracción")
        else:
            st.write("Lectura: ✅ Expansión")
            
        st.markdown(f"**ISM Servicios**")
        st.write(f"Dato: {ism_serv}")
        st.write("Lectura: ✅ Sostiene la economía")

    st.markdown("---")
    st.subheader("3. IMPACTO EN PRECIOS (Forecast Automático)")
    
    # Mostramos precios actuales
    st.caption(f"Precios hoy: NASDAQ: {market_data['NASDAQ']:.2f} | BTC: ${market_data['BITCOIN']:.2f}")

    c_nasdaq, c_btc = st.columns(2)
    
    with c_nasdaq:
        st.markdown("### 💻 NASDAQ 100")
        st.success(f"**3 Meses:** {forecast['nasdaq_3m']}")
        st.warning(f"**6 Meses:** {forecast['nasdaq_6m']}")
        
    with c_btc:
        st.markdown("### ₿ BITCOIN")
        st.success(f"**3 Meses:** {forecast['btc_3m']}")
        st.success(f"**6 Meses:** {forecast['btc_6m']}")

if __name__ == "__main__":
    main()