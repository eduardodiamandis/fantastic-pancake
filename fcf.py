from collections import defaultdict
from pathlib import Path
import sqlite3

import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(page_title="Gerador de Orçamentos", page_icon="🏛️")

# Função para conectar ao banco de dados
def connect_db():
    DB_FILENAME = Path(__file__).parent / "servicos.db"
    db_existente = DB_FILENAME.exists()
    conn = sqlite3.connect(DB_FILENAME)
    return conn, not db_existente

# Função para inicializar dados
def inicia_dados(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Servicos (
            ITEM INTEGER PRIMARY KEY AUTOINCREMENT,
            Servicos TEXT,
            UNID TEXT,
            QTDE REAL,
            MO REAL,
            TOTAL REAL,
            Custo_Total REAL GENERATED ALWAYS AS (QTDE * TOTAL) STORED
        )
    """)
    cursor.execute("""
        INSERT INTO Servicos (Servicos, UNID, QTDE, MO, TOTAL)
        VALUES
            ('Passagem de cabeamento estruturado', 'vb', 137.00, 135.00, 135.00),
            ('Montagem de rack', 'vb', 1.00, 940.00, 940.00)
    """)
    conn.commit()

# Função para carregar dados
def carrega_dados(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Servicos")
        data = cursor.fetchall()
    except sqlite3.OperationalError:
        return None
    df = pd.DataFrame(data, columns=["ITEM", "Servicos", "UNID", "QTDE", "MO", "TOTAL", "Custo_Total"])
    return df

# Função para atualizar dados
def atualizar_dados(conn, df, changes):
    cursor = conn.cursor()
    
    if changes.get("edited_rows"):
        for i, row in changes["edited_rows"].items():
            cursor.execute("""
                UPDATE Servicos 
                SET Servicos=?, UNID=?, QTDE=?, MO=?, TOTAL=?
                WHERE ITEM=?
            """, (row["Servicos"], row["UNID"], row["QTDE"], row["MO"], row["TOTAL"], df.loc[i, "ITEM"]))
    
    if changes.get("added_rows"):
        for row in changes["added_rows"]:
            cursor.execute("""
                INSERT INTO Servicos (Servicos, UNID, QTDE, MO, TOTAL)
                VALUES (?, ?, ?, ?, ?)
            """, (row["Servicos"], row["UNID"], row["QTDE"], row["MO"], row["TOTAL"]))
    
    if changes.get("deleted_rows"):
        for i in changes["deleted_rows"]:
            cursor.execute("DELETE FROM Servicos WHERE ITEM=?", (df.loc[i, "ITEM"],))
    
    conn.commit()

# Interface Streamlit
conn, db_novo = connect_db()
if db_novo:
    inicia_dados(conn)

df = carrega_dados(conn)

st.title("📊 Monte Seu Orçamento")
edited_df = st.data_editor(
    df,
    key="servicos_table",
    num_rows="dynamic",
    column_config={
        "MO": st.column_config.NumberColumn(format="R$%.2f"),
        "TOTAL": st.column_config.NumberColumn(format="R$%.2f"),
        "Custo_Total": st.column_config.NumberColumn(format="R$%.2f")
    }
)

if st.button("Confirmar Alterações"):
    atualizar_dados(conn, df, st.session_state.servicos_table)
    st.success("Dados atualizados!")