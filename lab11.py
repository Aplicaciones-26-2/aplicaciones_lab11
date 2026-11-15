import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as pe

st.set_page_config(layout="wide")
st.title("KORA-CLIENTES")
st.caption("Dashboard elaborado con fechas de clientes desde Agosto de 2025 hasta Septiembre de 2026")

pedidos = pd.read_csv("KORA_pedidos.csv",parse_dates=["fecha_pedido"])
clientes=pd.read_csv("KORA_clientes.csv",parse_dates=["fecha_registro"])

assert clientes.id_cliente.is_unique
assert pedidos.id_pedido.is_unique

filtro_canal = st.multiselect(label="CANALES",options= clientes.canal_adquisicion.unique(), default=clientes.canal_adquisicion.unique())
a, b, c, d = st.columns(4)

compradores = pedidos.groupby("id_cliente").agg(n_pedidos=("id_pedido","count"), ingreso_total=("ingreso_neto_cop","sum"), ultima_compra=("fecha_pedido","max")).reset_index()
clientes_filtro= clientes[clientes.canal_adquisicion.isin(filtro_canal)]
final = clientes_filtro.merge(compradores,how="left", on = "id_cliente", validate="one_to_one")

final["n_pedidos"] = final["n_pedidos"].fillna(0).astype(int)
final["ingreso_total"] = final["ingreso_total"].fillna(0)

fecha_corte = pd.Timestamp("2026-10-31")
final["dias_sin_compra"] = (fecha_corte - final["ultima_compra"]).dt.days

final["segmento"] = "En desarrollo"
final.loc[final.n_pedidos==1,"segmento"] = "Primerizos"
final.loc[final.n_pedidos>=3,"segmento"] = "Fieles"
final.loc[final.dias_sin_compra>90,"segmento"] = "En pausa"
final.loc[final.n_pedidos==0,"segmento"] = "Sin compra"

ciudades = st.sidebar.multiselect(label="CIUDADES",options= sorted(clientes.ciudad.unique()), default=sorted(clientes.ciudad.unique()))
segmentos = st.sidebar.multiselect(label="SEGMENTOS",options= sorted(final.segmento.unique()), default=sorted(final.segmento.unique()))
filtrado = final[final.ciudad.isin(ciudades)]
filtrado = filtrado[filtrado.segmento.isin(segmentos)]

compradores_FILTRADO = filtrado.query("n_pedidos>0")
numero_pedidos = compradores_FILTRADO.shape[0]

if numero_pedidos == 0:
    st.caption("No hay compradores con los filtros seleccionados")
else:
    recompra = (compradores_FILTRADO.n_pedidos.ge(2).mean())
    ingreso = filtrado.ingreso_total.sum()
    total_pedidos = filtrado.n_pedidos.sum()

    a.metric(label="COMPRADORES",value=numero_pedidos, border= True)
    b.metric(label="RECOMPRA",value=f"{recompra:.1%}", border= True)
    c.metric(label="INGRESO COP",value=f"{ingreso/1e6:.1f} M", border= True)
    d.metric(label="TICKET COP",value=f"{ingreso/total_pedidos:,.0f}", border= True)

    tabla = (filtrado.groupby("segmento")
             .size().reset_index(name="clientes"))
    fig = pe.bar(tabla, x="segmento",
                 y="clientes", text="clientes")
    st.plotly_chart(fig, width="stretch")

    pedidos_f = pedidos[pedidos.id_cliente.isin(filtrado.id_cliente)]

    cat = pedidos_f.groupby("categoria",
    as_index=False)["ingreso_neto_cop"].sum()
    fig = pe.bar(cat, x="ingreso_neto_cop",
                 y="categoria",orientation="h")
    st.plotly_chart(fig,width="stretch")

    pedidos_f["mes"] = ( pedidos_f.fecha_pedido.dt.to_period("M")
        .astype(str)
    )
    serie = pedidos_f.groupby("mes").size()
    fig = pe.line(x=serie.index,
                  y=serie.values, markers=True)
    st.plotly_chart(fig,width="stretch")