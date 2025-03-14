import streamlit as st
from orcamento_ui import OrcamentoUI

# Configurações iniciais do Streamlit
st.set_page_config(
    page_title="Orçamentos + Materiais",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# Execução principal
# =============================================================================
if __name__ == "__main__":
    ui = OrcamentoUI()
    ui.render()
