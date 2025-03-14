from pathlib import Path
import sqlite3
import pandas as pd

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