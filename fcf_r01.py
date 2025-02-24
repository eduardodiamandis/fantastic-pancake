from pathlib import Path
import sqlite3
import streamlit as st
import pandas as pd
import altair as alt

# Configurações iniciais do Streamlit
st.set_page_config(
    page_title="Orçamentos + Materiais",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# Módulo de Banco de Dados
# =============================================================================
class DatabaseManager:
    def __init__(self):
        self.db_path = Path(__file__).parent / "projetos.db"
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def init_db(self):
        cursor = self.conn.cursor()
        # Criação da tabela de serviços
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                unidade TEXT NOT NULL,
                quantidade REAL NOT NULL CHECK(quantidade >= 0),
                custo_unitario REAL NOT NULL CHECK(custo_unitario >= 0),
                total REAL GENERATED ALWAYS AS (ROUND(quantidade * custo_unitario, 2)) STORED
            )
        """)
        # Criação da tabela de materiais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                unidade TEXT NOT NULL,
                quantidade REAL NOT NULL CHECK(quantidade >= 0.0),
                custo_unitario REAL NOT NULL CHECK(custo_unitario >= 0.0),
                total REAL GENERATED ALWAYS AS (ROUND(quantidade * custo_unitario, 2)) STORED
            )
        """)
        # Inserir dados iniciais se a tabela estiver vazia
        for table in ['servicos', 'materiais']:
            if not cursor.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                if table == 'servicos':
                    cursor.execute("""
                        INSERT INTO servicos (descricao, unidade, quantidade, custo_unitario)
                        VALUES ('Exemplo serviço', 'un', 1, 100)
                    """)
                else:
                    cursor.execute("""
                        INSERT INTO materiais (item, unidade, quantidade, custo_unitario)
                        VALUES ('Exemplo material', 'un', 1, 100)
                    """)
        self.conn.commit()

    def load_data(self, table_name):
        df = pd.read_sql(f"SELECT * FROM {table_name}", self.conn)
        # Mapeia os nomes das colunas para exibição
        col_names = {
            'id': 'ID',
            'descricao': 'Descrição',
            'item': 'Item',
            'unidade': 'Unidade',
            'quantidade': 'Quantidade',
            'custo_unitario': 'Custo Unitário (R$)',
            'total': 'Total (R$)'
        }
        return df.rename(columns=col_names)

    def delete_item(self, table_name, item_id):
        with self.conn:
            self.conn.execute(
                f"DELETE FROM {table_name} WHERE id = ?",
                (item_id,)
            )

# =============================================================================
# Módulo de Interface e Lógica de Edição
# =============================================================================
class OrcamentoUI:
    def __init__(self):
        self.db = DatabaseManager()
        self._init_session_state()

    def _init_session_state(self):
        defaults = {
            'current_table': 'servicos',   # ou 'materiais' ou 'unificada'
            'servicos_data': None,
            'materiais_data': None,
            'edicoes_pendentes': False
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        with self.db as db:
            db.init_db()
            if st.session_state.servicos_data is None:
                st.session_state.servicos_data = db.load_data('servicos')
            if st.session_state.materiais_data is None:
                st.session_state.materiais_data = db.load_data('materiais')

    def _show_table_selector(self):
        cols = st.columns([1, 1, 1])
        with cols[0]:
            if st.button("🏗️ Serviços", disabled=st.session_state.current_table == 'servicos'):
                st.session_state.current_table = 'servicos'
        with cols[1]:
            if st.button("📦 Materiais", disabled=st.session_state.current_table == 'materiais'):
                st.session_state.current_table = 'materiais'
        with cols[2]:
            if st.button("🔀 Tabela Unificada"):
                st.session_state.current_table = 'unificada'

    def _save_changes(self, edited_df, table_name):
        with self.db as db:
            try:
                cursor = db.conn.cursor()
                original_df = st.session_state[f"{table_name}_data"]

                # Detecta deleções: IDs que existiam e não estão mais presentes
                original_ids = set(original_df['ID'])
                edited_ids = set(edited_df['ID'].dropna())
                deleted_ids = original_ids - edited_ids
                for item_id in deleted_ids:
                    db.delete_item(table_name, item_id)

                # Detecta novas linhas: linhas sem ID (NaN)
                new_rows = edited_df[edited_df['ID'].isna()]
                for _, row in new_rows.iterrows():
                    field_db = 'descricao' if table_name == 'servicos' else 'item'
                    display_field = 'Descrição' if table_name == 'servicos' else 'Item'
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} 
                        ({field_db}, unidade, quantidade, custo_unitario)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            row.get(display_field, 'Novo Item'),
                            row.get('Unidade', 'un'),
                            float(row.get('Quantidade', 0)),
                            float(row.get('Custo Unitário (R$)', 0))
                        )
                    )

                # Detecta edições: linhas com ID que tiveram mudanças
                edited_rows = edited_df[edited_df['ID'].notna()]
                for index, row in edited_rows.iterrows():
                    original_row = original_df[original_df['ID'] == row['ID']]
                    if original_row.empty:
                        continue
                    original_row = original_row.iloc[0]
                    display_field = 'Descrição' if table_name == 'servicos' else 'Item'
                    if (row[display_field] != original_row[display_field] or
                        row['Unidade'] != original_row['Unidade'] or
                        float(row['Quantidade']) != float(original_row['Quantidade']) or
                        float(row['Custo Unitário (R$)']) != float(original_row['Custo Unitário (R$)'])):
                        
                        field_db = 'descricao' if table_name == 'servicos' else 'item'
                        cursor.execute(
                            f"""
                            UPDATE {table_name}
                            SET {field_db} = ?,
                                unidade = ?,
                                quantidade = ?,
                                custo_unitario = ?
                            WHERE id = ?
                            """,
                            (
                                row[display_field],
                                row['Unidade'],
                                float(row['Quantidade']),
                                float(row['Custo Unitário (R$)']),
                                row['ID']
                            )
                        )
                db.conn.commit()
                # Recarrega os dados atualizados para a sessão
                st.session_state[f"{table_name}_data"] = db.load_data(table_name)
                st.session_state.edicoes_pendentes = False
                return True
            except sqlite3.Error as e:
                db.conn.rollback()
                st.error(f"Erro no banco de dados: {str(e)}")
                return False

    def _render_charts(self, data):
        st.subheader("📈 Análise de Custos")
        if data.empty:
            st.warning("Nenhum dado disponível para análise")
            return

        # Gráfico de barras por item
        y_field = 'Descrição' if 'Descrição' in data.columns else 'Item'
        bar_chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('sum(Total (R$)):Q', title='Custo Total (R$)'),
            y=alt.Y(field=y_field, sort='-x', title='Itens'),
            tooltip=[y_field, 'sum(Total (R$))']
        ).properties(
            title='Distribuição de Custos por Item',
            height=400
        )

        # Gráfico de pizza por categoria
        base = alt.Chart(data).encode(
            theta=alt.Theta("sum(Total (R$)):Q", stack=True),
            color=alt.Color('Unidade:N', legend=alt.Legend(title="Unidade"))
        )
        pie_chart = base.mark_arc(innerRadius=50).properties(
            title='Proporção por Unidade de Medida',
            width=400,
            height=400
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            st.altair_chart(bar_chart, use_container_width=True)
        with col2:
            st.altair_chart(pie_chart, use_container_width=True)

    def render_unified_table(self):
        with self.db as db:
            df_servicos = db.load_data('servicos')
            df_materiais = db.load_data('materiais')
        # Adiciona uma coluna para identificar o tipo de registro
        df_servicos['Tipo'] = 'Serviço'
        df_materiais['Tipo'] = 'Material'
        # Para unificar, renomeia a coluna "Descrição" para "Item" em serviços
        df_servicos = df_servicos.rename(columns={'Descrição': 'Item'})
        # Seleciona as colunas comuns
        colunas_comuns = ['ID', 'Item', 'Unidade', 'Quantidade', 'Custo Unitário (R$)', 'Total (R$)', 'Tipo']
        df_servicos = df_servicos[colunas_comuns]
        df_materiais = df_materiais[colunas_comuns]
        df_uniao = pd.concat([df_servicos, df_materiais], ignore_index=True)
        st.subheader("🔀 Tabela Unificada")
        st.dataframe(df_uniao)

    def render(self):
        st.title("📋 Sistema Integrado de Orçamentos")
        self._show_table_selector()
        current_table = st.session_state.current_table

        if current_table == 'unificada':
            self.render_unified_table()
        else:
            data_key = f"{current_table}_data"
            data = st.session_state[data_key]
            table_label = "Serviços" if current_table == 'servicos' else "Materiais"
            st.subheader(f"📝 Edição de {table_label}")

            edited_df = st.data_editor(
                data,
                key=f"editor_{current_table}",
                num_rows="dynamic",
                disabled=["ID", "Total (R$)"],
                column_config={
                    ('Descrição' if current_table == 'servicos' else 'Item'): st.column_config.TextColumn(
                        ('Descrição' if current_table == 'servicos' else 'Item'),
                        help="Descrição detalhada do item",
                        required=True
                    ),
                    'Unidade': st.column_config.SelectboxColumn(
                        "Unidade",
                        options=["un", "m²", "m", "kg", "hr", "lt"],
                        help="Selecione a unidade de medida",
                        required=True
                    ),
                    'Quantidade': st.column_config.NumberColumn(
                        "Quantidade",
                        min_value=0.0,
                        step=0.5,
                        format="%.2f",
                        help="Quantidade necessária"
                    ),
                    'Custo Unitário (R$)': st.column_config.NumberColumn(
                        "Custo Unitário",
                        min_value=0.0,
                        step=10.0,
                        format="R$ %.2f",
                        help="Custo por unidade"
                    )
                },
                on_change=lambda: st.session_state.update(edicoes_pendentes=True)
            )

            col1, col2 = st.columns([3, 1])
            with col1:
                if st.session_state.edicoes_pendentes:
                    if st.button("💾 Salvar Alterações", type="primary"):
                        with st.spinner("Salvando..."):
                            if self._save_changes(edited_df, current_table):
                                st.success("Dados salvos com sucesso!")
                    st.caption("⚠️ Alterações não salvas serão perdidas ao recarregar a página")
            with col2:
                total = edited_df['Total (R$)'].sum()
                st.metric(
                    label=f"Total {table_label}",
                    value=f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    help="Valor atualizado automaticamente"
                )

            self._render_charts(edited_df)

# =============================================================================
# Execução principal
# =============================================================================
if __name__ == "__main__":
    ui = OrcamentoUI()
    ui.render()
