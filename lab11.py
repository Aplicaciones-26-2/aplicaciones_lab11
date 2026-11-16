import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide")
st.title("KORA | Clientes")
st.caption("Clientes registrados de agosto 2025 a septiembre 2026\n\n"
           "Valores en COP")

clientes = pd.read_csv("KORA_clientes.csv", parse_dates=["fecha_registro"])
pedidos = pd.read_csv("KORA_pedidos.csv", parse_dates=["fecha_pedido"])

resumen = pedidos.groupby("id_cliente").agg(
    n_pedidos=("id_pedido", "nunique"),
    ingreso_total=("ingreso_neto_cop", "sum"),
    ultima_compra=("fecha_pedido", "max")
).reset_index()

perfil = clientes.merge(resumen, how="left", on="id_cliente", validate="one_to_one")

perfil["n_pedidos"] = perfil.n_pedidos.fillna(0)
perfil["ingreso_total"] = perfil.ingreso_total.fillna(0)

fecha_corte = pd.Timestamp("2026-10-31")
perfil["dias_sin_compra"] = (fecha_corte - perfil.ultima_compra).dt.days

def segmento(f):
    if f.n_pedidos == 0: return "Sin compra"
    if f.dias_sin_compra > 90: return "En pausa"
    if f.n_pedidos >= 3: return "Fieles"
    if f.n_pedidos == 1: return "Primerizos"
    return "En desarrollo"

perfil["segmento"] = perfil.apply(segmento, axis=1)

ciudades = st.sidebar.multiselect("Ciudad", sorted(perfil.ciudad.unique()), default=sorted(perfil.ciudad.unique()))

canales = st.sidebar.multiselect("Canal", sorted(perfil.canal_adquisicion.unique()),default=sorted(perfil.canal_adquisicion.unique()))
segmentos = st.sidebar.multiselect("Segmento", sorted(perfil.segmento.unique()), default=sorted(perfil.segmento.unique()))

preferencias = st.sidebar.multiselect("Preferencia declarada", sorted(perfil.preferencia_declarada.unique()), default=sorted(perfil.preferencia_declarada.unique()))


filtrado = perfil[perfil.ciudad.isin(ciudades)]
filtrado = filtrado[filtrado.canal_adquisicion.isin(canales)]
filtrado = filtrado[filtrado.segmento.isin(segmentos)]
filtrado = filtrado[filtrado.preferencia_declarada.isin(preferencias)]

compradores = filtrado.query("n_pedidos > 0")
una_compra = filtrado.query("n_pedidos == 1")

st.caption("**¿En qué canal conviene probar una campaña de segunda compra?**")
st.caption("**1**. La tasa de recompra es: compradores con 2 o más pedidos / compradores (clientes con 1 o más pedidos). Es un porcentaje, entonces no muestra cuánta gente hay en cada canal. Un canal puede tener la tasa más baja pero muy pocos compradores, y ahí la campaña le llegaría a poca gente. El número de clientes con exactamente una compra muestra cuántas personas compraron una vez y no han vuelto. Esas son las personas a las que va dirigida la campaña. Por eso hay que mirar los dos datos.")

if len(compradores) == 0:
    st.caption("No hay compradores con los filtros seleccionados.")
else:
    recompra = compradores.n_pedidos.ge(2).mean()
    ingreso = filtrado.ingreso_total.sum()
    total_pedidos = filtrado.n_pedidos.sum()
    pct_una_compra = len(una_compra) / len(compradores)

    a, b, c, d = st.columns(4)
    a.metric("Compradores", len(compradores), border=True)
    b.metric("Recompra", f"{recompra:.1%}", border=True)
    c.metric("Ingreso COP", f"{ingreso/1e6:.1f} M", border=True)
    d.metric("Ticket COP", f"{ingreso/total_pedidos:,.0f}", border=True)

    e, f = st.columns(2)
    e.metric("Clientes con exactamente una compra", len(una_compra), border=True)
    f.metric("% de compradores con una sola compra", f"{pct_una_compra:.1%}", border=True)

    tabla = (filtrado.groupby("segmento")
             .size().reset_index(name="clientes"))
    fig = px.bar(tabla, x="segmento", y="clientes", text="clientes",
                 title="Clientes por segmento")
    st.plotly_chart(fig, width="stretch")

    pedidos_f = pedidos[pedidos.id_cliente.isin(filtrado.id_cliente)]

    cat = pedidos_f.groupby("categoria", as_index=False)["ingreso_neto_cop"].sum()
    fig = px.bar(cat, x="ingreso_neto_cop", y="categoria", orientation="h", title="Ingreso neto por categoría (COP)")
    st.plotly_chart(fig, width="stretch")

    pedidos_f["mes"] = (pedidos_f.fecha_pedido.dt.to_period("M").astype(str))
    serie = pedidos_f.groupby("mes").size()
    fig = px.line(x=serie.index, y=serie.values, markers=True, title="Pedidos por mes", labels={"x": "mes", "y": "pedidos"})
    st.plotly_chart(fig, width="stretch")

    por_canal = (
        compradores.groupby("canal_adquisicion")
        .agg(
            compradores=("id_cliente", "count"),
            con_2_o_mas=("n_pedidos", lambda x: (x >= 2).sum()),
            una_compra=("n_pedidos", lambda x: (x == 1).sum()),
            recompra_pct=("n_pedidos", lambda x: (x >= 2).mean() * 100)
        )
        .reset_index()
    )

    por_canal = por_canal.sort_values("recompra_pct", ascending=False)
    fig = px.bar(por_canal, x="canal_adquisicion", y="recompra_pct",
                 text="compradores",
                 hover_data=["compradores", "con_2_o_mas"],
                 labels={"canal_adquisicion": "Canal",
                         "recompra_pct": "% compradores con 2+ pedidos",
                         "compradores": "Compradores",
                         "con_2_o_mas": "Compradores con 2+ pedidos"},
                 title="Porcentaje de compradores con dos o más pedidos por canal")
    st.plotly_chart(fig, width="stretch")
    st.caption("Usamos barras porque queremos comparar la tasa entre canales, y las barras sirven para comparar categorías. Las ordenamos de mayor a menor para que se lea más fácil. El número de cada barra es la cantidad de compradores de ese canal, y en el hover también sale cuántos tienen 2 o más pedidos.")

    por_canal = por_canal.sort_values("una_compra", ascending=True)
    fig = px.bar(por_canal, x="una_compra", y="canal_adquisicion", orientation="h", 
                 text="una_compra", hover_data=["compradores", "recompra_pct"], 
                 labels={"canal_adquisicion": "Canal", "una_compra": "Clientes",
                         "compradores": "Compradores",
                         "recompra_pct": "% recompra"},
                 title="Clientes con exactamente un pedido por canal")
    st.plotly_chart(fig, width="stretch")

    mayor_volumen = por_canal.sort_values("una_compra", ascending=False).canal_adquisicion.iloc[0]
    menor_tasa = por_canal.sort_values("recompra_pct", ascending=True).canal_adquisicion.iloc[0]
    if mayor_volumen == menor_tasa:
        coincide = "sí coinciden"
    else:
        coincide = "no coinciden"

    st.caption(f"El canal con más clientes de una sola compra no necesariamente es el de menor tasa de recompra, porque un canal con muchos compradores puede tener más clientes de una sola compra aunque su tasa no sea la más baja. Con los filtros que están puestos ahora, el canal con más clientes de una sola compra es {mayor_volumen} y el de menor tasa de recompra es {menor_tasa}, entonces {coincide}.")

st.caption("**5**. Probamos el tablero con todos los filtros (1.038 compradores y 66,1% de recompra); con solo la preferencia Tecnología y las ciudades Bogotá y Medellín (bajan a 183 compradores y 58 con una sola compra, y las dos gráficas nuevas cambian); y con solo el segmento 'Sin compra', donde no hay compradores y sale un aviso en vez de las métricas.")

st.caption("**6**. Recomendamos hacer el piloto en el canal Redes sociales. Es el canal con más clientes de una sola compra (147 personas) y tiene la tasa de recompra más baja (59,6%), mientras que Orgánico tiene 75,5%. Una limitación es que no sabemos por qué estos clientes no volvieron ni si aceptaron que los contactemos. Para evaluar el piloto mediríamos la tasa de recompra, comparando un grupo que recibe la campaña con otro que no la recibe.")