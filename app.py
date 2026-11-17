import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import db
import scraper
import notifier

# Símbolo de moneda predeterminado: Sol Peruano
MONEDA = "S/."

# Configuración general de la página Streamlit
st.set_page_config(
    page_title="Rastreador de Precios y Ofertas (Soles)",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .badge-deal {
        background-color: #d4edda;
        color: #155724;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar base de datos de forma segura
try:
    db.init_db()
except Exception as e:
    st.error(f"⚠️ Error conectando a la base de datos PostgreSQL: {e}")
    st.stop()

# --- Encabezado ---
st.title("🏷️ Rastreador Automático de Precios y Ofertas")
st.caption(f"Monitorea productos en Steam, Mercado Libre, tiendas online y más en Soles Peruanos ({MONEDA}).")

# --- Barra lateral: Notificaciones y Registro de nuevo producto ---
st.sidebar.header("📧 Notificaciones por Correo")

smtp_listo = notifier.esta_configurado()
if smtp_listo:
    cfg_smtp = notifier.obtener_config_smtp()
    st.sidebar.success(f"🟢 Activo: alertas a **{cfg_smtp['destinatario']}**")
    if st.sidebar.button("📨 Enviar correo de prueba", use_container_width=True):
        with st.sidebar.status("Enviando correo de prueba..."):
            ok, msj = notifier.enviar_correo_prueba()
            if ok:
                st.sidebar.success(msj)
            else:
                st.sidebar.error(msj)
else:
    st.sidebar.warning("🟡 Correo no configurado. Configura tu correo en el archivo `.env` para recibir alertas.")
    with st.sidebar.expander("ℹ️ ¿Cómo activar alertas a mi correo?"):
        st.markdown("""
        1. Abre el archivo `.env` en la raíz del proyecto.
        2. Configura tu cuenta de Gmail:
           - `SMTP_USER=tu_correo@gmail.com`
           - `SMTP_PASSWORD=tu_contraseña_de_aplicacion`
           - `EMAIL_NOTIFICACION=tu_correo_destino@gmail.com`
        3. *Nota para Gmail:* Requiere crear una **Contraseña de Aplicación** de 16 letras en [Google App Passwords](https://myaccount.google.com/apppasswords).
        """)

st.sidebar.divider()
st.sidebar.header("➕ Registrar Nuevo Producto")

with st.sidebar.form("form_nuevo_producto", clear_on_submit=True):
    nombre_prod = st.text_input("Nombre del producto*", placeholder="Ej. Tarjeta de Video RTX 5070 o Terraria")
    
    # Obtener lista de tiendas de la BD
    try:
        tiendas_disponibles = db.obtener_tiendas()
        opciones_tiendas = {t["nombre"]: t["id_tienda"] for t in tiendas_disponibles}
    except Exception as e:
        opciones_tiendas = {"Steam": 2, "Mercado Libre": 3, "Books to Scrape": 1, "Otro": 5}

    nombre_tienda = st.selectbox("Tienda*", options=list(opciones_tiendas.keys()))
    url_prod = st.text_input("URL del producto*", placeholder="https://www.mercadolibre.com.pe/... o https://store.steampowered.com/...")
    precio_objetivo = st.number_input(f"Precio objetivo ({MONEDA})*", min_value=0.0, step=1.0, format="%.2f")
    
    # Permitir ingresar precio inicial opcionalmente si el usuario ya lo conoce
    precio_inicial_manual = st.number_input(f"Precio actual conocido ({MONEDA}) - Opcional", min_value=0.0, step=1.0, format="%.2f", help="Útil si la tienda tiene protecciones anti-bot que impiden el scraping automático.")
    
    scrapear_inmediato = st.checkbox("Intentar extraer precio actual automáticamente con el scraper", value=True)
    
    submit_producto = st.form_submit_button("Guardar Producto", use_container_width=True)

    if submit_producto:
        if not nombre_prod.strip() or not url_prod.strip():
            st.sidebar.error("❌ Por favor completa el nombre y la URL.")
        elif precio_objetivo <= 0:
            st.sidebar.error("❌ El precio objetivo debe ser mayor a 0.")
        else:
            try:
                id_tienda = opciones_tiendas.get(nombre_tienda)
                if not id_tienda:
                    id_tienda = db.obtener_o_crear_tienda(nombre_tienda)
                
                nuevo_id = db.crear_producto(nombre_prod, id_tienda, url_prod, precio_objetivo)
                st.sidebar.success(f"✅ ¡Producto '{nombre_prod}' registrado con éxito!")
                
                precio_registrado = None
                
                # Si el usuario ingresó un precio manual inicial:
                if precio_inicial_manual > 0:
                    db.registrar_precio(nuevo_id, precio_inicial_manual)
                    precio_registrado = precio_inicial_manual
                    st.sidebar.info(f"💵 Precio inicial ingresado: {MONEDA} {precio_inicial_manual:.2f}")
                # O si marcó intentar scrapear:
                elif scrapear_inmediato:
                    with st.spinner("Consultando precio con el scraper..."):
                        resultado = scraper.extraer_precio(url_prod)
                        if resultado["precio"] is not None:
                            db.registrar_precio(nuevo_id, resultado["precio"])
                            precio_registrado = resultado["precio"]
                            st.sidebar.info(f"💵 Precio inicial detectado: {MONEDA} {resultado['precio']:.2f}")
                        else:
                            st.sidebar.warning(f"⚠️ {resultado['error']}")
                
                # Si de entrada está en oferta, disparar notificación si corresponde
                if precio_registrado is not None and precio_registrado <= precio_objetivo and smtp_listo:
                    ok, msj = notifier.enviar_alerta_oferta(
                        nombre_producto=nombre_prod,
                        tienda=nombre_tienda,
                        url_producto=url_prod,
                        precio_actual=precio_registrado,
                        precio_objetivo=precio_objetivo,
                        moneda=MONEDA
                    )
                    if ok:
                        db.actualizar_estado_notificacion(nuevo_id, True)
                        st.sidebar.success("📧 ¡Alerta de oferta enviada a tu correo!")
                
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Error al guardar producto: {e}")

# --- Sección de Métricas Globales y Botón de Actualización ---
try:
    productos_resumen = db.obtener_resumen_productos()
except Exception as e:
    st.error(f"Error cargando productos: {e}")
    productos_resumen = []

col_btn, col_m1, col_m2, col_m3 = st.columns([2, 1.5, 1.5, 1.5])

with col_btn:
    st.write("")
    if st.button("🔄 Actualizar precios ahora", use_container_width=True, type="primary"):
        if not productos_resumen:
            st.warning("No hay productos guardados para actualizar.")
        else:
            progress_bar = st.progress(0, text="Iniciando actualización de precios...")
            total = len(productos_resumen)
            actualizados = 0
            bloqueados = 0
            alertas_enviadas = 0

            for idx, prod in enumerate(productos_resumen):
                progress_bar.progress((idx + 1) / total, text=f"Consultando: {prod['nombre']} ({idx+1}/{total})")
                res = scraper.extraer_precio(prod["url_producto"])
                
                if res["precio"] is not None:
                    nuevo_precio = res["precio"]
                    db.registrar_precio(prod["id_producto"], nuevo_precio)
                    actualizados += 1

                    p_obj = float(prod["precio_objetivo"])
                    ya_notificado = bool(prod.get("notificado"))

                    if nuevo_precio <= p_obj:
                        if not ya_notificado and smtp_listo:
                            ok, msj = notifier.enviar_alerta_oferta(
                                nombre_producto=prod["nombre"],
                                tienda=prod["tienda"],
                                url_producto=prod["url_producto"],
                                precio_actual=nuevo_precio,
                                precio_objetivo=p_obj,
                                precio_minimo=float(prod["precio_minimo"]) if prod["precio_minimo"] else nuevo_precio,
                                moneda=MONEDA
                            )
                            if ok:
                                db.actualizar_estado_notificacion(prod["id_producto"], True)
                                alertas_enviadas += 1
                    else:
                        if ya_notificado:
                            db.actualizar_estado_notificacion(prod["id_producto"], False)
                else:
                    bloqueados += 1

            progress_bar.empty()
            
            mensajes_resumen = [f"Actualizados automáticamente: {actualizados}"]
            if alertas_enviadas > 0:
                mensajes_resumen.append(f"📧 {alertas_enviadas} alerta(s) de oferta enviada(s)")
            if bloqueados > 0:
                mensajes_resumen.append(f"ℹ️ {bloqueados} producto(s) requieren ingreso manual (anti-bot)")
                
            st.info(" | ".join(mensajes_resumen))
            st.rerun()

total_prods = len(productos_resumen)
ofertas_activas = sum(1 for p in productos_resumen if p.get("alerta_alcanzada"))
sin_precio = sum(1 for p in productos_resumen if p.get("precio_actual") is None)

with col_m1:
    st.metric("Total Productos", total_prods)
with col_m2:
    st.metric("Ofertas Alcanzadas 🎯", ofertas_activas)
with col_m3:
    st.metric("Pendientes de lectura", sin_precio)

st.divider()

# --- Tabla Resumen de Productos ---
st.subheader("📋 Resumen de Productos y Estado de Precios")

if not productos_resumen:
    st.info("💡 Aún no has registrado ningún producto. Usa el formulario de la barra lateral para agregar el primero.")
else:
    tabla_datos = []
    for p in productos_resumen:
        p_act = f"{MONEDA} {float(p['precio_actual']):.2f}" if p["precio_actual"] is not None else "Sin lectura"
        p_min = f"{MONEDA} {float(p['precio_minimo']):.2f}" if p["precio_minimo"] is not None else "Sin lectura"
        p_obj = f"{MONEDA} {float(p['precio_objetivo']):.2f}"
        
        # Alerta visual si precio actual <= objetivo
        if p["precio_actual"] is not None:
            if p["alerta_alcanzada"]:
                notif_txt = " (📧 Notificado)" if p.get("notificado") else ""
                estado = f"🎯 ¡EN OFERTA!{notif_txt}"
            else:
                diferencia = float(p["precio_actual"]) - float(p["precio_objetivo"])
                estado = f"⏳ Esperando (+{MONEDA} {diferencia:.2f})"
        else:
            estado = "⚠️ Sin precio (Ingresar abajo)"

        ultima_act = p["ultima_actualizacion"].strftime("%Y-%m-%d %H:%M") if p["ultima_actualizacion"] else "Nunca"

        tabla_datos.append({
            "ID": p["id_producto"],
            "Producto": p["nombre"],
            "Tienda": p["tienda"],
            "Precio Actual": p_act,
            "Mínimo Histórico": p_min,
            "Precio Objetivo": p_obj,
            "Estado / Alerta": estado,
            "Última Actualización": ultima_act,
            "URL": p["url_producto"]
        })

    df_resumen = pd.DataFrame(tabla_datos)
    
    st.dataframe(
        df_resumen.drop(columns=["URL"]),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# --- Sección: Gráfico interactivo y detalles por producto ---
st.subheader("📈 Evolución de Precios y Gestión por Producto")

if productos_resumen:
    col_sel, col_action = st.columns([3, 1])
    with col_sel:
        opciones_prod = {f"{p['nombre']} (ID: {p['id_producto']} - {p['tienda']})": p["id_producto"] for p in productos_resumen}
        prod_seleccionado_txt = st.selectbox("Selecciona un producto para ver su gráfica y gestionar su precio:", options=list(opciones_prod.keys()))
        prod_id_seleccionado = opciones_prod[prod_seleccionado_txt]

    prod_detalle = next((p for p in productos_resumen if p["id_producto"] == prod_id_seleccionado), None)

    with col_action:
        st.write("")
        if st.button("🗑️ Eliminar este producto", type="secondary", use_container_width=True):
            if db.eliminar_producto(prod_id_seleccionado):
                st.success("Producto eliminado correctamente.")
                st.rerun()

    # Formulario para registrar o actualizar el precio manualmente
    with st.expander("✏️ Registrar o actualizar precio manualmente (Ideal para Mercado Libre o tiendas con Anti-Bot)", expanded=(prod_detalle["precio_actual"] is None)):
        st.caption(f"Si la tienda de este producto bloquea el rastreo automatizado, puedes registrar aquí su precio actual:")
        with st.form(f"form_manual_{prod_id_seleccionado}"):
            col_in, col_btn_manual = st.columns([3, 1])
            with col_in:
                val_defecto = float(prod_detalle["precio_actual"]) if prod_detalle["precio_actual"] is not None else 0.0
                precio_manual_val = st.number_input(f"Precio actual visto en la tienda ({MONEDA})", min_value=0.01, step=10.0, format="%.2f", value=val_defecto if val_defecto > 0 else 100.0)
            with col_btn_manual:
                st.write("")
                submit_manual = st.form_submit_button("Guardar Precio", use_container_width=True)

            if submit_manual:
                if precio_manual_val > 0:
                    db.registrar_precio(prod_id_seleccionado, precio_manual_val)
                    p_obj = float(prod_detalle["precio_objetivo"])
                    
                    if precio_manual_val <= p_obj:
                        if smtp_listo and not prod_detalle.get("notificado"):
                            ok, msj = notifier.enviar_alerta_oferta(
                                nombre_producto=prod_detalle["nombre"],
                                tienda=prod_detalle["tienda"],
                                url_producto=prod_detalle["url_producto"],
                                precio_actual=precio_manual_val,
                                precio_objetivo=p_obj,
                                moneda=MONEDA
                            )
                            if ok:
                                db.actualizar_estado_notificacion(prod_id_seleccionado, True)
                                st.success("🎉 ¡Precio guardado y alerta de oferta enviada a tu correo!")
                    else:
                        st.success(f"✅ ¡Precio de {MONEDA} {precio_manual_val:.2f} registrado correctamente!")
                    st.rerun()

    # Obtener el historial para la gráfica
    historial = db.obtener_historial(prod_id_seleccionado)
    
    if not historial:
        st.warning("Este producto aún no cuenta con lecturas de precios en el historial. Puedes ingresar la primera en el formulario de arriba.")
    else:
        df_historial = pd.DataFrame(historial)
        df_historial["precio"] = df_historial["precio"].astype(float)
        df_historial["fecha_formato"] = pd.to_datetime(df_historial["fecha_registro"])

        # Crear figura interactiva con Plotly
        fig = go.Figure()

        # Línea de historial de precios
        fig.add_trace(go.Scatter(
            x=df_historial["fecha_formato"],
            y=df_historial["precio"],
            mode="lines+markers",
            name="Precio Registrado",
            line=dict(color="#1f77b4", width=3),
            marker=dict(size=8, color="#0d47a1")
        ))

        # Línea de referencia del Precio Objetivo
        if prod_detalle:
            p_obj_val = float(prod_detalle["precio_objetivo"])
            fig.add_trace(go.Scatter(
                x=[df_historial["fecha_formato"].min(), df_historial["fecha_formato"].max()],
                y=[p_obj_val, p_obj_val],
                mode="lines",
                name=f"Precio Objetivo ({MONEDA} {p_obj_val:.2f})",
                line=dict(color="#2ca02c", width=2, dash="dash")
            ))

        fig.update_layout(
            title=f"Historial de precios: {prod_detalle['nombre']}",
            xaxis_title="Fecha y Hora",
            yaxis_title=f"Precio ({MONEDA})",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"🔗 [Visitar página del producto en la tienda]({prod_detalle['url_producto']})")
