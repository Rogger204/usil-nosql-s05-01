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
    st.error("❌ No se encontró el secreto `mongo.uri` en `.streamlit/secrets.toml`")
    st.stop()

@st.cache_resource
def get_client(uri):
    return MongoClient(uri)

try:
    client = get_client(mongo_uri)
    # CAMBIO: Usando la base de datos y colección de la imagen
    db = client["sample_supplies"]
    col_sales = db["sales"]
    
    client.admin.command("ping")
    st.sidebar.success("✅ Conectado a sample_supplies.sales")
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# ─── Filtros de Búsqueda ───
st.markdown("---")
col1, col2 = st.columns([2, 1])

with col1:
    # Filtro por ubicación de la tienda (Store Location)
    store_location = st.text_input(
        "📍 Buscar por ubicación de tienda",
        placeholder="Ej: Denver, Seattle, London, New York"
    )

with col2:
    # Filtro por método de compra
    metodo_compra = st.multiselect(
        "Método de compra",
        ["In store", "Online", "Phone"],
        default=["In store", "Online", "Phone"]
    )

limite = st.slider("Cantidad de registros a mostrar", 5, 100, 20)

# ─── Construcción de la Query ───
query = {}
if store_location:
    query["storeLocation"] = {"$regex": store_location, "$options": "i"}
if metodo_compra:
    query["purchaseMethod"] = {"$in": metodo_compra}

# Ejecutar consulta
resultados_raw = list(col_sales.find(query).limit(limite))

if not resultados_raw:
    st.warning("No se encontraron ventas con esos criterios.")
else:
    # ─── Procesamiento de Datos para Tabla ───
    datos_tabla = []
    for r in resultados_raw:
        # Extraer info del cliente (es un objeto anidado)
        customer = r.get("customer", {})
        
        datos_tabla.append({
            "ID Venta": str(r.get("_id")),
            "Fecha": r.get("saleDate").strftime("%Y-%m-%d") if r.get("saleDate") else "—",
            "Tienda": r.get("storeLocation", "—"),
            "Método": r.get("purchaseMethod", "—"),
            "Cupón": "✅" if r.get("couponUsed") else "❌",
            "Email Cliente": customer.get("email", "—"),
            "Edad Cliente": customer.get("age", "—"),
            "Género": customer.get("gender", "—"),
            "Satisfacción (1-5)": customer.get("satisfaction", "—"),
            "Items": len(r.get("items", []))
        })

    df = pd.DataFrame(datos_tabla)

    # ─── Visualización ───
    st.markdown(f"### 📋 Listado de {len(df)} ventas encontradas")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── Sección de Detalles (Expansores) ───
    st.markdown("### 📦 Detalle de artículos por venta")
    for i, r in enumerate(resultados_raw):
        tienda = r.get("storeLocation")
        metodo = r.get("purchaseMethod")
        with st.expander(f"Venta {df.iloc[i]['ID Venta']} - {tienda} ({metodo})"):
            # Mostrar los items de esa venta específica
            items = r.get("items", [])
            if items:
                df_items = pd.DataFrame(items)
                # Formatear precios si existen
                if 'price' in df_items.columns:
                    df_items['price'] = df_items['price'].apply(lambda x: f"${float(str(x)):,.2f}")
                st.table(df_items[['name', 'tags', 'price', 'quantity']])
            else:
                st.write("No hay detalles de artículos.")
