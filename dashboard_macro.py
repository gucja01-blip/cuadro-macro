import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Macro Dashboard Pro V6", layout="centered", page_icon="🏛️")

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# --- 1. GESTIÓN DE CLAVE API ---
try:
    FRED_API_KEY = st.secrets["FRED_KEY"]
except:
    # ⚠️ PEGA TU CLAVE AQUÍ SI ES NECESARIO EN LOCAL
    FRED_API_KEY = 'PON_TU_CLAVE_AQUI'

# --- 2. FUNCIONES DE DATOS ---

def obtener_datos_macro(api_key):
    datos = {}
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    try:
        fred = Fred(api_key=api_key)
        m2 = fred.get_series('M2SL', observation_start=start_date)
        fci = fred.get_series('NFCI', observation_start=start_date)
        
        m2.index = pd.to_datetime(m2.index)
        
        datos['m2_serie'] = m2
        datos['fci_serie'] = fci
        datos['m2_actual'] = m2.iloc[-1] 
        datos['m2_previo'] = m2.iloc[-2]
        datos['fci_actual'] = fci.iloc[-1]
        datos['api_activa'] = True
    except Exception as e:
        st.error(f"Error FED: {e}")
        fechas = pd.date_range(start='2023-01-01', periods=24, freq='M')
        datos['m2_serie'] = pd.Series([20800 + i*10 for i in range(24)], index=fechas)
        datos['fci_serie'] = pd.Series([-0.5] * 24, index=fechas)
        datos['m2_actual'] = 21000
        datos['m2_previo'] = 20800
        datos['fci_actual'] = -0.5
        datos['api_activa'] = False
    return datos

def obtener_precios_mercado():
    tickers = {'NASDAQ': '^IXIC', 'BITCOIN': 'BTC-USD', 'GOLD': 'GC=F', 'DXY': 'DX-Y.NYB'}
    precios = {}
    historicos = {}
    for nombre, simbolo in tickers.items():
        try:
            ticker = yf.Ticker(simbolo)
            hist = ticker.history(period="2y")
            if not hist.empty:
                precios[nombre] = hist['Close'].iloc[-1]
                historicos[nombre] = hist['Close']
            else:
                precios[nombre] = 0
                historicos[nombre] = pd.Series([])
        except:
            precios[nombre] = 0
            historicos[nombre] = pd.Series([])
    return precios, historicos

# --- FUNCIÓN GRÁFICA (ALTAIR) ---
def preparar_datos_correlacion(serie_activo, serie_m2, nombre_activo):
    if serie_activo.empty or serie_m2.empty:
        return pd.DataFrame()

    # Resamplear activo a fin de mes
    activo_mensual = serie_activo.resample('M').last()
    activo_mensual.index = pd.to_datetime(activo_mensual.index).to_period('M').to_timestamp()
    
    serie_m2_clean = serie_m2.copy()
    serie_m2_clean.index = pd.to_datetime(serie_m2_clean.index).to_period('M').to_timestamp()

    # Combinar
    df = pd.DataFrame({
        'Fecha': activo_mensual.index,
        nombre_activo: activo_mensual.values,
        'Liquidez M2 (Billions)': serie_m2_clean[activo_mensual.index].values 
    })
    
    df = df.dropna()
    df_melted = df.melt('Fecha', var_name='Indicador', value_name='Valor')
    return df_melted

# --- 3. LÓGICA DE NEGOCIO ---

def analizar_macro(m2_now, m2_prev, fci):
    trend_m2 = "Subiendo" if m2_now >= m2_prev else "Bajando"
    senal_m2 = "🟢 Reflación" if trend_m2 == "Subiendo" else "🔴 Desinflación"
    estado_fci = "Relajadas" if fci < 0 else "Restrictivas"
    return trend_m2, senal_m2, estado_fci

def generar_pronostico(trend_m2, estado_fci, ism_manuf):
    p = {}
    trending_up = (trend_m2 == "Subiendo")
    
    p['nasdaq'] = "↗️ Alcista" if trending_up else "➡️ Lateral"
    if ism_manuf < 50: p['nasdaq'] += " (⚠️ Riesgo ISM)"
    p['btc'] = "🚀 Muy Alcista" if (trending_up and "Relajadas" in estado_fci) else "🔁 Volátil"
    p['gold'] = "↗️ Alcista (Reserva valor)" if trending_up else "➡️ Neutral"
    p['dxy'] = "↘️ Bajista (Debilidad)" if "Relajadas" in estado_fci else "↗️ Alcista (Fortaleza)"
    return p

# --- 4. INTERFAZ VISUAL ---

def main():
    st.title("🏛️ VISIÓN MACRO GLOBAL V6")
    
    # --- MENÚ DE INPUTS MANUALES (CORREGIDO) ---
    with st.expander("📝 PULSA PARA CAMBIAR FECHA Y DATOS ISM (Simulación)", expanded=False):
        st.caption("Configura tu escenario económico manual:")
        c_mes, c_ano = st.columns(2)
        with c_mes:
            mes_seleccionado = st.selectbox("Mes", 
                ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=0)
        with c_ano:
            ano_seleccionado = st.selectbox("Año", ["2024", "2025", "2026"], index=1)
        fecha_texto = f"{mes_seleccionado} {ano_seleccionado}"
        st.markdown("---")
        
        c_i1, c_i2 = st.columns(2)
        
        # AQUÍ ESTABA EL ERROR: Ahora usamos nombres explícitos (value=, min_value=, etc.)
        with c_i1: 
            ism_manuf = st.number_input(
                "🏭 Manufacturero", 
                value=48.2, 
                min_value=0.0, 
                max_value=100.0, 
                step=0.1, 
                format="%.1f"
            )
        with c_i2: 
            ism_serv = st.number_input(
                "🛎️ Servicios", 
                value=52.6, 
                min_value=0.0, 
                max_value=100.0, 
                step=0.1, 
                format="%.1f"
            )

    # Carga y Lógica
    with st.spinner("Conectando con la FED y Mercados..."):
        macro = obtener_datos_macro(FRED_API