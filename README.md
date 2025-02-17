# Gerador de Orçamentos

Este projeto é uma aplicação web desenvolvida com **Streamlit** que permite gerenciar serviços e gerar orçamentos automaticamente. Ele utiliza um banco de dados **SQLite** para armazenar os dados dos serviços e calcula o custo total com base na quantidade e no valor unitário.

---
## Funcionalidades
- **Criação e gerenciamento de banco de dados**:
  - Cria automaticamente uma tabela `inventory` no SQLite.
  - Insere dados iniciais de serviços.
  - Calcula automaticamente o custo total (`Custo_Total`) com base na quantidade (`QTDE`) e no valor unitário (`TOTAL`).

---
- **Funcionalidades futuras** 🏗️ -- ainda em produção --:
  - Inserção de novos serviços via interface.
  - Edição e exclusão de serviços existentes.
  - Geração de relatórios de orçamentos em PDF.

# Estrutura do Banco de Dados

A tabela `inventory` possui as seguintes colunas:

| Coluna         | Tipo        | Descrição                                      |
|----------------|-------------|------------------------------------------------|
| `ITEM`         | INTEGER     | Chave primária com autoincremento.             |
| `Servicos`     | TEXT        | Descrição do serviço.                          |
| `UNID`         | TEXT        | Unidade de medida do serviço.                  |
| `QTDE`         | REAL        | Quantidade do serviço.                         |
| `MO`           | REAL        | Mão de obra ou custo adicional.                |
| `TOTAL`        | REAL        | Valor unitário do serviço.                     |
| `Custo_Total`  | REAL        | Custo total calculado automaticamente (`QTDE * TOTAL`). |

---
