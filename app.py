import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import re

# --- CONFIGURAÇÃO BLINDADA (Lê direto da Nuvem) ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        # Se não achar, tenta variável de ambiente (backup)
        api_key = os.getenv("GEMINI_API_KEY")
except FileNotFoundError:
    api_key = None

# Se a chave estiver vazia, avisa na tela
if not api_key:
    st.error("🚨 ERRO CRÍTICO: Não encontrei a chave 'GEMINI_API_KEY' nos Secrets.")
    st.info("Vá em 'Manage App' > 'Settings' > 'Secrets' e verifique se está assim: GEMINI_API_KEY = \"sua_chave\"")
    st.stop()

# Configura a IA
genai.configure(api_key=api_key)

st.set_page_config(page_title="Glumi", page_icon="🛍️", layout="centered")

# --- CSS: CORES DA MARCA GLUMI (FINAL) ---
st.markdown("""
<style>
    /* 1. Ocultar TUDO que é do Streamlit (Menu, Footer, Botão Vermelho) */
    #MainMenu {visibility: hidden; display: none;}
    footer {visibility: hidden; display: none;}
    header {visibility: hidden; display: none;}
    .stAppDeployButton {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    /* 2. Ajuste do Layout Mobile */
    .stApp { background-color: #FFFFFF; }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 8rem !important;
    }

    /* 3. Input Fixo (Ajuste Fino) */
    .stChatInput {
        position: fixed; bottom: 0; left: 0; width: 100% !important;
        padding: 1rem; background: white !important; z-index: 99999;
        border-top: 1px solid #eee;
    }
    
    /* ... (Mantenha o resto do CSS dos balões que já estava bom) ... */
    </style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    csv_path = "produtos_glumi_v2.csv"
    if not os.path.exists(csv_path): return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, sep=';')
        cols = ['preco_venda', 'preco_original']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

df = load_data()

# --- IA SETUP ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key and "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
if api_key: genai.configure(api_key=api_key)

def consultar_ia(pergunta, estoque_df):
    txt = "\n".join([f"ID:{r['id']}|Item:{r['nome']}|R${r['preco_venda']}|Cat:{r['categoria']}" for _, r in estoque_df.iterrows()])
    prompt = f"Voce é Vendedor simpatico da Glumi. Estoque: {txt}. Cliente: '{pergunta}'. Responda curto. Finalize com [ID_DO_PRODUTO] se achar algo."
    
    for m in ['gemini-2.0-flash-lite-preview-02-05', 'gemini-flash-latest', 'gemini-1.5-flash']:
        try: return genai.GenerativeModel(m).generate_content(prompt).text
        except: continue
    return "Erro de conexão."

# --- INTERFACE ---

# 1. HEADER (Logo Centralizada e Limpa)
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    logo_path = os.path.join("imagens_produtos", "logoglumi.png")
    if os.path.exists(logo_path):
        # width=100 garante que não fica gigante
        st.image(logo_path, width=120) 
    else:
        st.markdown("<h3 style='text-align:center'>Glumi</h3>", unsafe_allow_html=True)

# 2. CHAT
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! O que você procura?"}]

for msg in st.session_state.messages:
    # Renderiza mensagens sem os ícones padrões do Streamlit
    with st.chat_message(msg["role"]):
        # Limpa o ID da mensagem de texto
        content_show = re.sub(r"\[.*?\]", "", msg["content"])
        st.markdown(content_show)

# 3. INPUT
if prompt := st.chat_input("Digite aqui..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun() # Recarrega para mostrar a msg do usuário imediatamente

# 4. LÓGICA DE RESPOSTA (Separada para renderizar após o rerun)
if st.session_state.messages[-1]["role"] == "user":
    if not api_key:
        st.warning("Sem API Key")
    else:
        with st.chat_message("assistant"):
            with st.spinner("..."):
                resp = consultar_ia(st.session_state.messages[-1]["content"], df)
                
                # Extrai ID
                match = re.search(r"\[(.*?)\]", resp)
                id_prod = match.group(1) if match else None
                txt_limpo = resp.replace(f"[{id_prod}]", "") if id_prod else resp
                
                st.markdown(txt_limpo)
                
                # CARD DO PRODUTO
                if id_prod:
                    row = df[df['id'] == id_prod]
                    if not row.empty:
                        r = row.iloc[0]
                        
                        # Renderiza Card HTML
                        html_card = f"""
                        <div class="product-card">
                            <div class="prod-name">{r['nome']}</div>
                            <div class="prod-price">R$ {float(r['preco_venda']):,.2f}</div>
                            <div class="prod-id">Ref: {r['id']}</div>
                        </div>
                        """
                        
                        # Imagem separada (Streamlit lida melhor com img fora do HTML puro)
                        col_img, col_txt = st.columns([1, 2])
                        with col_img:
                            if pd.notna(r['imagem_local']) and os.path.exists(str(r['imagem_local'])):
                                st.image(str(r['imagem_local']), use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/100", use_container_width=True)
                        with col_txt:
                            st.markdown(html_card, unsafe_allow_html=True)


        st.session_state.messages.append({"role": "assistant", "content": resp})



