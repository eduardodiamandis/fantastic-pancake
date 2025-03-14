import sqlite3
import streamlit as st
import pandas as pd
import altair as alt
from database_manager import DatabaseManager
from typing import Optional, Dict, Any

class OrcamentoUI:
    def __init__(self):
        self.db = DatabaseManager()
        self._init_session_state()

    def _init_session_state(self) -> None:
        """Inicializa o estado da sessão do Streamlit."""
        defaults = {
            'current_table': 'servicos',
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

    def _show_table_selector(self) -> None:
        """Exibe os botões para selecionar a tabela atual."""
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

    def _save_changes(self, edited_df: pd.DataFrame, table_name: str) -> bool:
        """Salva as alterações feitas na tabela."""
        with self.db as db:
            try:
                cursor = db.conn.cursor()
                original_df = st.session_state[f"{table_name}_data"]

                original_ids = set(original_df['ID'])
                edited_ids = set(edited_df['ID'].dropna())
                deleted_ids = original_ids - edited_ids
                for item_id in deleted_ids:
                    db.delete_item(table_name, item_id)

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
                st.session_state[f"{table_name}_data"] = db.load_data(table_name)
                st.session_state.edicoes_pendentes = False
                return True
            except sqlite3.Error as e:
                db.conn.rollback()
                st.error(f"Erro no banco de dados: {str(e)}")
                return False

    def _render_charts(self, data: pd.DataFrame) -> None:
        """Renderiza gráficos de análise de custos."""
        st.subheader("📈 Análise de Custos")
        if data.empty:
            st.warning("Nenhum dado disponível para análise")
            return

        y_field = 'Descrição' if 'Descrição' in data.columns else 'Item'
        bar_chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('mean(Custo Unitário (R$)):Q', title='Custo Unitário Médio (R$)'),
            y=alt.Y(field=y_field, sort='-x', title='Itens'),
            tooltip=[y_field, 'mean(Custo Unitário (R$))']
        ).properties(
            title='Distribuição de Custos Unitários Médios por Item',
            height=400
        )

        base = alt.Chart(data).encode(
            theta=alt.Theta("mean(Custo Unitário (R$)):Q", stack=True),
            color=alt.Color('Unidade:N', legend=alt.Legend(title="Unidade"))
        )
        pie_chart = base.mark_arc(innerRadius=50).properties(
            title='Proporção de Custos Unitários Médios por Unidade de Medida',
            width=400,
            height=400
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            st.altair_chart(bar_chart, use_container_width=True)
        with col2:
            st.altair_chart(pie_chart, use_container_width=True)

    def render_unified_table(self) -> None:
        """Renderiza a tabela unificada de serviços e materiais."""
        with self.db as db:
            df_servicos = db.load_data('servicos')
            df_materiais = db.load_data('materiais')
        df_servicos['Tipo'] = 'Serviço'
        df_materiais['Tipo'] = 'Material'
        df_servicos = df_servicos.rename(columns={'Descrição': 'Item'})
        colunas_comuns = ['ID', 'Item', 'Unidade', 'Quantidade', 'Custo Unitário (R$)', 'Total (R$)', 'Tipo']
        df_servicos = df_servicos[colunas_comuns]
        df_materiais = df_materiais[colunas_comuns]
        df_uniao = pd.concat([df_servicos, df_materiais], ignore_index=True)
        st.subheader("🔀 Tabela Unificada")
        st.dataframe(df_uniao)

    def render(self) -> None:
        """Renderiza a interface principal do sistema de orçamentos."""
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
                disabled=["ID","Total (R$)"],
                column_config={
                    ('Descrição' if current_table == 'servicos' else 'Item'): st.column_config.TextColumn(
                        ('Descrição' if current_table == 'servicos' else 'Item'),
                        help="Descrição detalhada do item",
                        required=True
                    ),
                    'Unidade': st.column_config.SelectboxColumn(
                        "Unidade",
                        options=["un", "m²", "m", "kg", "hr", "pç", "lt", "vb", "rl"],
                        help="Selecione a unidade de medida",
                        required=True
                    ),
                    'Quantidade': st.column_config.NumberColumn(
                        "Quantidade",
                        width='small',
                        step=None,
                        format="%.2f",
                        help="Quantidade necessária"
                    ),
                    'Custo Unitário (R$)': st.column_config.NumberColumn(
                        "Custo Unitário",
                        step=0.05,
                        format="%.2f",
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
                    value=f"R$ {total:,.2f}",
                    help="Valor atualizado automaticamente"
                )

            self._render_charts(edited_df)