import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Glumi", page_icon="🛍️", layout="centered")

# --- 2. CONFIGURAÇÃO BLINDADA DA API ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.getenv("GEMINI_API_KEY")
except FileNotFoundError:
    api_key = None

if not api_key:
    st.error("🚨 ERRO CRÍTICO: Chave GEMINI_API_KEY não encontrada.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. CSS CORRETIVO (SOLUÇÃO DA TELA BRANCA) ---
st.markdown("""
<style>
    /* 1. Ocultar interface do Streamlit */
    #MainMenu, footer, header {visibility: hidden; display: none !important;}
    .stAppDeployButton {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}

    /* 2. Ajuste do Fundo */
    .stApp { background-color: #FFFFFF; }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 8rem !important;
    }

    /* 3. BARRA DE INPUT (CORRIGIDA) */
    .stChatInput {
        position: fixed; bottom: 0; left: 0; width: 100% !important;
        padding: 1rem; 
        background-color: #ffffff !important; 
        z-index: 99999;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    
    /* FORÇA A COR DA LETRA PARA PRETO (NUCLEAR) */
    .stChatInput textarea {
        background-color: #f0f2f6 !important; /* Fundo cinza claro */
        color: #000000 !important;             /* Letra PRETA */
        -webkit-text-fill-color: #000000 !important;
        caret-color: #E91E63 !important;       /* Cursor Rosa */
        border: 1px solid #ddd !important;
    }
    
    /* Cor do Placeholder (Texto 'Digite aqui...') */
    .stChatInput textarea::placeholder {
        color: #666666 !important;
    }

    /* Botão de Enviar */
    [data-testid="stChatInputSubmitButton"] {
        background-color: transparent !important;
        color: #E91E63 !important; /* Ícone Rosa */
    }

    /* 4. BALÕES DE CHAT */
    /* Esconde avatares */
    .stChatMessage .st-emotion-cache-1p1m4ay, 
    div[data-testid="stChatMessageAvatar"] { display: none !important; }

    div[data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 0.5rem 0; border: none !important;
    }

    /* Assistente (Rosa) */
    div[data-testid="stChatMessage"]:nth-child(even) {
        flex-direction: row; justify-content: flex-start;
    }
    div[data-testid="stChatMessage"]:nth-child(even) .stMarkdown {
        background-color: #E91E63 !important; 
        color: #FFFFFF !important;
        text-align: left; 
        border-radius: 20px 20px 20px 5px;
        padding: 12px 18px; 
        box-shadow: 0 2px 5px rgba(233, 30, 99, 0.2);
    }
    div[data-testid="stChatMessage"]:nth-child(even) p { color: #FFFFFF !important; }

    /* Usuário (Cinza) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        flex-direction: row-reverse; justify-content: flex-end;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) .stMarkdown {
        background-color: #E0E0E0 !important; /* Cinza um pouco mais escuro pra contraste */
        color: #000000 !important;
        text-align: right; 
        border-radius: 20px 20px 5px 20px;
        padding: 12px 18px;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) p { color: #000000 !important; }

    /* Card de Produto */
    .product-card {
        background: white; border-radius: 12px; padding: 10px;
        margin-top: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #eee;
    }
    .prod-name { font-weight: 600; color: #333 !important; font-size: 0.9rem; margin-bottom: 5px; }
    .prod-price { color: #00a650 !important; font-weight: 800; font-size: 1.2rem; }
    .prod-id { color: #aaa !important; font-size: 0.7rem; }
</style>
""", unsafe_allow_html=True)

# --- 4. CARREGAMENTO DE DADOS ---
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

# --- 5. LÓGICA DA IA ---
def consultar_ia(pergunta, estoque_df):
    txt = "\n".join([f"ID:{r['id']}|Item:{r['nome']}|R${r['preco_venda']}|Cat:{r['categoria']}" for _, r in estoque_df.iterrows()])
    prompt = f"Vendedor simpatico Glumi. Estoque: {txt}. Cliente: '{pergunta}'. Responda curto. Finalize com [ID_DO_PRODUTO] se achar. Se não achar, não invente ID."
    
    for m in ['gemini-2.0-flash-lite-preview-02-05', 'gemini-flash-latest', 'gemini-1.5-flash']:
        try: return genai.GenerativeModel(m).generate_content(prompt).text
        except: continue
    return "Erro de conexão."

# --- 6. INTERFACE ---

# Header com Logo
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    logo_path = os.path.join("imagens_produtos", "logoglumi.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=120) 
    else:
        st.markdown("<h3 style='text-align:center; color:#333'>Glumi</h3>", unsafe_allow_html=True)

# Chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! O que você procura?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content_show = re.sub(r"\[.*?\]", "", msg["content"])
        st.markdown(content_show)

# Input
if prompt := st.chat_input("Digite aqui..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Resposta
if st.session_state.messages[-1]["role"] == "user":
    if not api_key:
        st.warning("Sem API Key")
    else:
        with st.chat_message("assistant"):
            with st.spinner("..."):
                resp = consultar_ia(st.session_state.messages[-1]["content"], df)
                
                match = re.search(r"\[(.*?)\]", resp)
                id_prod = match.group(1) if match else None
                txt_limpo = resp.replace(f"[{id_prod}]", "") if id_prod else resp
                
                st.markdown(txt_limpo)
                
                if id_prod:
                    row_df = df[df['id'] == id_prod]
                    if not row_df.empty:
                        r = row_df.iloc[0]
                        
                        html_card = f"""
                        <div class="product-card">
                            <div class="prod-name">{r['nome']}</div>
                            <div class="prod-price">R$ {float(r['preco_venda']):,.2f}</div>
                            <div class="prod-id">Ref: {r['id']}</div>
                        </div>
                        """
                        
                        col_img, col_txt = st.columns([1, 2])
                        with col_img:
                            # Lógica corrigida de imagem
                            img_path = str(r['imagem_local'])
                            
                            if os.path.exists(img_path):
                                st.image(img_path, use_container_width=True)
                            elif pd.notna(r.get('imagem_url')) and str(r['imagem_url']).startswith('http'):
                                st.image(str(r['imagem_url']), use_container_width=True)
                            else:
                                st.write("📷") 

                        with col_txt:
                            st.markdown(html_card, unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": resp})
