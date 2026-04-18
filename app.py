import streamlit as st
from pymongo import MongoClient
import pandas as pd

# ─── Configuración de página ───
st.set_page_config(page_title="Explorador de Ventas", page_icon="🛍️", layout="wide")

st.title("🛍️ Explorador de Ventas — Sample Supplies")
st.caption("Consulta el historial de ventas y métodos de compra en MongoDB Atlas")

# ─── Conexión a MongoDB Atlas ───
try:
    mongo_uri = st.secrets["mongo"]["uri"]
except KeyError:
    st.error("❌ No se encontró el secreto `mongo.uri` en `.streamlit/secrets.toml`.")
    st.stop()

@st.cache_resource
def get_client(uri):
    return MongoClient(uri)

try:
    client = get_client(mongo_uri)
    db = client["sample_supplies"]
    col_sales = db["sales"]
    
    # Test de conexión
    client.admin.command("ping")
    st.sidebar.success("✅ Conectado a sample_supplies.sales")
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# ─── Filtros de Búsqueda (Diseño Compacto) ───
st.markdown("---")
# Dividimos en 3 columnas para integrar la cantidad en la misma fila
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    store_location = st.text_input(
        "📍 Ubicación de tienda",
        placeholder="Ej: Seattle, Denver, London..."
    )

with col2:
    metodo_compra = st.multiselect(
        "Método de compra",
        ["In store", "Online", "Phone"],
        default=["In store", "Online", "Phone"]
    )

with col3:
    # Sustituimos la línea del slider por un selector desplegable más integrado
    limite = st.selectbox(
        "Registros a mostrar",
        [5, 10, 20, 50, 100],
        index=2  # Valor por defecto: 20
    )

# ─── Construcción de la Query ───
query = {}
if store_location:
    query["storeLocation"] = {"$regex": store_location, "$options": "i"}
if metodo_compra:
    query["purchaseMethod"] = {"$in": metodo_compra}

# Ejecutar consulta en MongoDB
resultados_raw = list(col_sales.find(query).limit(limite))

if not resultados_raw:
    st.warning("No se encontraron ventas con esos criterios.")
else:
    # ─── Procesamiento de Datos para Tabla Principal ───
    datos_tabla = []
    for r in resultados_raw:
        customer = r.get("customer", {})
        
        datos_tabla.append({
            "ID Venta": str(r.get("_id")),
            "Fecha": r.get("saleDate").strftime("%Y-%m-%d") if r.get("saleDate") else "—",
            "Tienda": r.get("storeLocation", "—"),
            "Método": r.get("purchaseMethod", "—"),
            "Cupón": "✅" if r.get("couponUsed") else "❌",
            "Email Cliente": customer.get("email", "—"),
            "Edad": customer.get("age", "—"),
            "Satisfacción": f"{customer.get('satisfaction', '—')}/5",
            "Items": len(r.get("items", []))
        })

    df = pd.DataFrame(datos_tabla)

    # ─── Visualización de Resultados ───
    st.markdown(f"### 📋 Listado de {len(df)} ventas encontradas")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── Detalle Expandible por Venta ───
    st.markdown("### 📦 Detalle de artículos por venta")
    for i, r in enumerate(resultados_raw):
        tienda = r.get("storeLocation", "Sin ubicación")
        metodo = r.get("purchaseMethod", "Sin método")
        venta_id = df.iloc[i]['ID Venta']
        
        with st.expander(f"Venta {venta_id} — {tienda} ({metodo})"):
            items = r.get("items", [])
            if items:
                df_items = pd.DataFrame(items)
                # Formatear la columna de precio a moneda si existe
                if 'price' in df_items.columns:
                    # Convertimos a float por si viene como Decimal128 de MongoDB
                    df_items['price'] = df_items['price'].apply(lambda x: f"${float(str(x)):,.2f}")
                
                # Reorganizar columnas para mejor lectura
                columnas_ver = [c for c in ['name', 'quantity', 'price', 'tags'] if c in df_items.columns]
                st.table(df_items[columnas_ver])
            else:
                st.info("Esta venta no contiene artículos registrados.")
