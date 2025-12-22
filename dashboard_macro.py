import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cuadro de Mando Macro", layout="centered")

# --- 1. CONFIGURACIÓN DE API ---
# ⚠️ ¡OJO! Vuelve a pegar aquí tu clave de FRED que conseguiste antes.
FRED_API_KEY = '4d80754d7562963786ce89113fd95e9e' 

# --- 2. FUNCIONES DE EXTRACCIÓN DE DATOS ---

def obtener_datos_macro(api_key):
    """Obtiene datos históricos y actuales de FRED."""
    datos = {}
    # Fecha de inicio para los gráficos (2 años atrás)
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    try:
        fred = Fred(api_key=api_key)
        
        # M2SL: Liquidez
        m2 = fred.get_series('M2SL', observation_start=start_date)
        # NFCI: Condiciones Financieras
        fci = fred.get_series('NFCI', observation_start=start_date)
        
        # Guardamos la serie completa para el gráfico
        datos['m2_serie'] = m2
        datos['fci_serie'] = fci
        
        # Guardamos los datos puntuales para los cálculos
        datos['m2_actual'] = m2.iloc[-1]
        datos['m2_previo'] = m2.iloc[-2]
        datos['fci_actual'] = fci.iloc[-1]
        datos['api_activa'] = True
        
    except Exception as e:
        st.warning(f"⚠️ Usando datos simulados (Error API: {e})")
        # Datos simulados para que no falle si hay error
        fechas = pd.date_range(start='2023-01-01', periods=24, freq='M')
        datos['m2_serie'] = pd.Series([20000 + i*50 for i in range(24)], index=fechas)
        datos['fci_serie'] = pd.Series([-0.5 + i*0.01 for i in range(24)], index=fechas)
        
        datos['m2_actual'] = 21000 
        datos['m2_previo'] = 20800
        datos['fci_actual'] = -0.5
        datos['api_activa'] = False
        
    return datos

def obtener_precios_mercado():
    """Obtiene precios históricos de mercado."""
    tickers = {
        'NASDAQ': '^IXIC',
        'BITCOIN': 'BTC-USD'
    }
    precios = {}
    historicos = {}
    
    for nombre, simbolo in tickers.items():
        ticker = yf.Ticker(simbolo)
        # Pedimos 1 año de historia para el gráfico
        hist = ticker.history(period="1y")
        precios[nombre] = hist['Close'].iloc[-1]
        historicos[nombre] = hist['Close']
        
    return precios, historicos

# --- 3. LÓGICA DE NEGOCIO ---

def analizar_liquidez(m2_actual, m2_previo):
    if m2_actual > m2_previo:
        return "↗️ Subiendo", "Reflación (Liquidez al alza)", "🟢 Bullish"
    else:
        return "↘️ Bajando", "Desinflación (Liquidez a la baja)", "🔴 Bearish"

def analizar_fci(fci_nivel):
    if fci_nivel < 0:
        return "Relajadas (Dinero barato)", "🟢 Semáforo Verde"
    else:
        return "Restrictivas (Dinero caro)", "🔴 Semáforo Rojo"

def generar_pronostico(tendencia_m2, estado_fci, ism_manuf):
    pronostico = {'nasdaq_3m': '', 'nasdaq_6m': '', 'btc_3m': '', 'btc_6m': ''}
    
    # Lógica NASDAQ
    if "Subiendo" in tendencia_m2:
        pronostico['nasdaq_3m'] = "↗️ Alcista (Liquidez busca rendimiento)"
    else:
        pronostico['nasdaq_3m'] = "➡️ Lateral/Bajista"
        
    if ism_manuf < 50:
        pronostico['nasdaq_6m'] = "⚠️ Riesgo de Recesión (ISM < 50)"
    else:
        pronostico['nasdaq_6m'] = "↗️ Alcista Sólido"

    # Lógica BITCOIN
    if "Subiendo" in tendencia_m2 and "Relajadas" in estado_fci:
        pronostico['btc_3m'] = "🚀 Muy Alcista (Canario en la mina)"
        pronostico['btc_6m'] = "↗️ Alcista (Mientras FCI siga relajado)"
    else:
        pronostico['btc_3m'] = "🔁 Volátil"
        pronostico['btc_6m'] = "⚠️ Precaución"
        
    return pronostico

# --- 4. INTERFAZ DE USUARIO ---

def main():
    st.title("📱 CUADRO DE MANDO MACRO")
    st.markdown("---")

    # Obtener Datos
    macro_data = obtener_datos_macro(FRED_API_KEY)
    market_prices, market_history = obtener_precios_mercado()
    
    # Inputs Manuales
    with st.sidebar:
        st.header("Ajustes Manuales")
        ism_manuf = st.number_input("ISM Manufacturero", value=48.2)
        ism_serv = st.number_input("ISM Servicios", value=52.6)
        st.info("Nota: Los gráficos muestran los últimos 1-2 años.")

    # Procesar Lógica
    tendencia_m2_txt, estado_macro, senal_m2 = analizar_liquidez(macro_data['m2_actual'], macro_data['m2_previo'])
    estado_fci_txt, senal_fci = analizar_fci(macro_data['fci_actual'])
    forecast = generar_pronostico(tendencia_m2_txt, estado_fci_txt, ism_manuf)

    # --- MOSTRAR DATOS ---
    st.info(f"**Estado General:** {estado_macro}")

    # SECCIÓN 1: MACRO
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. EL COMBUSTIBLE 🚰")
        st.metric("Liquidez Global (M2)", f"${macro_data['m2_actual']:,.0f}B", delta=tendencia_m2_txt)
        st.caption(f"Señal: {senal_m2}")
        
    with col2:
        st.subheader("Condiciones (FCI)")
        st.metric("Nivel FCI", f"{macro_data['fci_actual']:.2f}", delta="Bajo es bueno", delta_color="inverse")
        st.caption(f"Estado: {estado_fci_txt}")

    # GRÁFICOS MACRO (NUEVO: Usamos 'expander' para que no ocupe mucho espacio si no quieres verlo)
    with st.expander("📊 Ver Gráfico de Liquidez y FCI"):
        st.markdown("**Evolución de la Liquidez (M2)**")
        st.line_chart(macro_data['m2_serie'])
        
        st.markdown("**Condiciones Financieras (Bajo 0 = Bueno)**")
        st.line_chart(macro_data['fci_serie'])

    st.markdown("---")

    # SECCIÓN 2: MERCADO
    st.subheader("3. IMPACTO EN PRECIOS")
    
    tab1, tab2 = st.tabs(["💻 NASDAQ", "₿ BITCOIN"])
    
    with tab1:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.metric("Precio Actual", f"{market_prices['NASDAQ']:.2f}")
            st.success(f"3M: {forecast['nasdaq_3m']}")
            st.warning(f"6M: {forecast['nasdaq_6m']}")
        with col_b:
            st.line_chart(market_history['NASDAQ'])
            
    with tab2:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.metric("Precio Actual", f"${market_prices['BITCOIN']:,.2f}")
            st.success(f"3M: {forecast['btc_3m']}")
            st.success(f"6M: {forecast['btc_6m']}")
        with col_b:
            st.line_chart(market_history['BITCOIN'])

if __name__ == "__main__":
    main()