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
    # ⚠️ SI ESTÁS EN LOCAL, PEGA TU CLAVE AQUÍ
    FRED_API_KEY = 'PON_TU_CLAVE_AQUI'

# --- 2. FUNCIONES DE DATOS ---

def obtener_datos_macro(api_key):
    datos = {}
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    try:
        fred = Fred(api_key=api_key)
        m2 = fred.get_series('M2SL', observation_start=start_date)
        fci = fred.get_series('NFCI', observation_start=start_date)
        
        # Aseguramos que el índice es datetime
        m2.index = pd.to_datetime(m2.index)
        fci.index = pd.to_datetime(fci.index)
        
        datos['m2_serie'] = m2
        datos['fci_serie'] = fci
        
        # Usamos iloc[-1] con seguridad
        if not m2.empty:
            datos['m2_actual'] = m2.iloc[-1] 
            datos['m2_previo'] = m2.iloc[-2]
        else:
            datos['m2_actual'] = 0
            datos['m2_previo'] = 0
            
        if not fci.empty:
            datos['fci_actual'] = fci.iloc[-1]
        else:
            datos['fci_actual'] = 0
            
        datos['api_activa'] = True
    except Exception as e:
        # Datos simulados de emergencia
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

# --- FUNCIÓN GRÁFICA CORREGIDA (SOLUCIÓN KEYERROR) ---
def preparar_datos_correlacion(serie_activo, serie_m2, nombre_activo):
    """
    Combina datos usando merge para evitar errores si faltan fechas en M2.
    """
    if serie_activo.empty or serie_m2.empty:
        return pd.DataFrame()

    # 1. Preparar Activo (Fin de mes)
    activo_mensual = serie_activo.resample('M').last()
    # Forzamos fecha al inicio del mes para coincidir con M2
    activo_mensual.index = pd.to_datetime(activo_mensual.index).to_period('M').to_timestamp()
    df_activo = pd.DataFrame({'Fecha': activo_mensual.index, nombre_activo: activo_mensual.values})

    # 2. Preparar M2
    serie_m2_clean = serie_m2.copy()
    serie_m2_clean.index = pd.to_datetime(serie_m2_clean.index).to_period('M').to_timestamp()
    df_m2 = pd.DataFrame({'Fecha': serie_m2_clean.index, 'Liquidez M2 (Billions)': serie_m2_clean.values})

    # 3. FUSIÓN SEGURA (MERGE)
    # 'inner' solo mantiene las filas donde existen datos en AMBOS lados.
    # Si M2 no tiene el dato de este mes, se descarta y no da error.
    df_merged = pd.merge(df_activo, df_m2, on='Fecha', how='inner')
    
    if df_merged.empty:
        return pd.DataFrame()

    # 4. Formato para Altair
    df_melted = df_merged.melt('Fecha', var_name='Indicador', value_name='Valor')
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
    
    # --- MENÚ MANUAL ---
    with st.expander("📝 PULSA PARA CAMBIAR FECHA Y DATOS ISM (Simulación)", expanded=False):
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
        with c_i1: 
            ism_manuf = st.number_input("🏭 Manufacturero", value=48.2, min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        with c_i2: 
            ism_serv = st.number_input("🛎️ Servicios", value=52.6, min_value=0.0, max_value=100.0, step=0.1, format="%.1f")

    # Carga
    with st.spinner("Conectando con la FED y Mercados..."):
        macro = obtener_datos_macro(FRED_API_KEY)
        precios, historia = obtener_precios_mercado()
        
    trend_m2, senal_m2, estado_fci = analizar_macro(macro['m2_actual'], macro['m2_previo'], macro['fci_actual'])
    forecast = generar_pronostico(trend_m2, estado_fci, ism_manuf)

    # --- DASHBOARD ---
    st.markdown(f"### 📅 Escenario Manual: {fecha_texto}")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Liquidez M2 (FED)", f"{trend_m2}", delta=senal_m2, delta_color="off")
    with col2: st.metric("Condic. FCI (FED)", f"{macro['fci_actual']:.2f}", delta="< 0 es Bueno", delta_color="inverse")
    with col3: st.metric("ISM Manuf. (Tú)", f"{ism_manuf}", delta="Expansión > 50")
    with col4: st.metric("ISM Serv. (Tú)", f"{ism_serv}", delta="Sostiene Eco")

    st.markdown("---")
    st.subheader("🌊 La Ola Monetaria: Correlaciones M2")
    st.caption("Evolución de los activos (Azul) vs Liquidez Global M2 (Verde).")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💻 NASDAQ vs M2", "₿ BITCOIN vs M2", "🥇 ORO vs M2", "💵 DÓLAR vs M2"])

    def mostrar_correlacion(nombre_activo, ticker_key, forecast_key):
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric(f"Precio {nombre_activo}", f"${precios[ticker_key]:,.2f}")
            st.info(f"Visión Monetarista: {forecast[forecast_key]}")
        
        with c2:
            # LLAMADA A LA FUNCIÓN CORREGIDA
            df_chart = preparar_datos_correlacion(historia[ticker_key], macro['m2_serie'], nombre_activo)
            
            if df_chart.empty:
                st.warning(f"Esperando actualización de datos M2 para correlacionar con {nombre_activo}.")
                return

            base = alt.Chart(df_chart).encode(x=alt.X('Fecha:T', axis=alt.Axis(title=None, format='%Y-%m')))

            linea_activo = base.transform_filter(alt.datum.Indicador == nombre_activo).mark_line(
                color='#1f77b4', strokeWidth=3
            ).encode(
                y=alt.Y('Valor:Q', axis=alt.Axis(title=nombre_activo, titleColor='#1f77b4')),
                tooltip=['Fecha', alt.Tooltip('Valor', title='Precio', format=',.0f')]
            )

            linea_m2 = base.transform_filter(alt.datum.Indicador == 'Liquidez M2 (Billions)').mark_line(
                color='#2ca02c', strokeWidth=3, strokeDash=[5,5]
            ).encode(
                y=alt.Y('Valor:Q', axis=alt.Axis(title='M2 Billions (FED)', titleColor='#2ca02c', orient='right')),
                tooltip=['Fecha', alt.Tooltip('Valor', title='M2 FED', format=',.0f')]
            )
            
            chart_final = alt.layer(linea_activo, linea_m2).resolve_scale(y='independent').properties(height=350).interactive()
            st.altair_chart(chart_final, use_container_width=True)

    with tab1: mostrar_correlacion("NASDAQ", "NASDAQ", "nasdaq") 
    with tab2: mostrar_correlacion("BITCOIN", "BITCOIN", "btc")  
    with tab3: mostrar_correlacion("ORO", "GOLD", "gold")       
    with tab4: mostrar_correlacion("DÓLAR DXY", "DXY", "dxy")    

if __name__ == "__main__":
    main()