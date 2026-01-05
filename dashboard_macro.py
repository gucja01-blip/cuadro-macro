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
    """Obtiene precios de Yahoo Finance."""
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

# --- 3. LÓGICA DE NEGOCIO ---

def analizar_macro(m2_now, m2_prev, fci):
    trend_m2 = "Subiendo" if m2_now > m2_prev else "Bajando"
    senal_m2 = "🟢 Reflación" if trend_m2 == "Subiendo" else "🔴 Desinflación"
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
    
    # --- BARRA LATERAL (MEJORADA) ---
    with st.sidebar:
        st.header("⚙️ Configuración Manual")
        
        # 1. Selector de FECHA
        st.markdown("**📅 Fecha de los datos ISM**")
        col_mes, col_ano = st.columns(2)
        with col_mes:
            mes_seleccionado = st.selectbox("Mes", 
                ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Sept", "Oct", "Nov", "Dic"], index=0)
        with col_ano:
            ano_seleccionado = st.selectbox("Año", ["2024", "2025", "2026"], index=1)
        
        fecha_referencia = f"{mes_seleccionado} {ano_seleccionado}"
        
        st.markdown("---")
        
        # 2. Inputs de ISM (Editables)
        # step=0.1 habilita los botones +/- y format="%.1f" asegura que veas un decimal
        st.markdown(f"**Indicar datos de: {fecha_referencia}**")
        
        ism_manuf = st.number_input(
            "🏭 ISM Manufacturero", 
            value=48.2, 
            step=0.1, 
            format="%.1f",
            help="Escribe el dato o usa los botones +/-"
        )
        
        ism_serv = st.number_input(
            "🛎️ ISM Servicios", 
            value=52.6, 
            step=0.1, 
            format="%.1f",
            help="Escribe el dato o usa los botones +/-"
        )
        
        st.info("Nota: Los datos macro se actualizan al cambiar estos valores.")

    # Carga de datos automáticos
    macro = obtener_datos_macro(FRED_API_KEY)
    precios, historia = obtener_precios_mercado()

    # Lógica
    trend_m2, senal_m2, estado_fci = analizar_macro(macro['m2_actual'], macro['m2_previo'], macro['fci_actual'])
    forecast = generar_pronostico(trend_m2, estado_fci, ism_manuf)

    # --- DASHBOARD SUPERIOR (MACRO) ---
    st.caption(f"Tracking en tiempo real | Datos manuales: **{fecha_referencia}**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Liquidez M2", f"{trend_m2}", delta=senal_m2, delta_color="off")
    with col2:
        st.metric("Condic. FCI", f"{macro['fci_actual']:.2f}", delta="< 0 es Bueno", delta_color="inverse")
    with col3:
        # Aquí mostramos el dato manual
        st.metric("ISM Manuf.", f"{ism_manuf}", delta="Expansión > 50")
    with col4:
        # Aquí mostramos el dato manual
        st.metric("ISM Serv.", f"{ism_serv}", delta="Sostiene Eco")

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