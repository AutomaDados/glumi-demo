import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha do Streamlit) ---
st.set_page_config(page_title="Glumi", page_icon="🛍️", layout="centered")

# --- 2. CONFIGURAÇÃO BLINDADA DA API ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        # Se não achar, tenta variável de ambiente (backup)
        api_key = os.getenv("GEMINI_API_KEY")
except FileNotFoundError:
    api_key = None

# Se a chave estiver vazia, avisa na tela e PARA tudo
if not api_key:
    st.error("🚨 ERRO CRÍTICO: Não encontrei a chave 'GEMINI_API_KEY' nos Secrets.")
    st.info("Vá em 'Manage App' > 'Settings' > 'Secrets' e verifique se está assim: GEMINI_API_KEY = \"sua_chave\"")
    st.stop()

# Configura a IA
genai.configure(api_key=api_key)

# --- 3. CSS PROFISSIONAL ---
st.markdown("""
<style>
    /* Ocultar elementos padrão do Streamlit */
    #MainMenu {visibility: hidden; display: none;}
    footer {visibility: hidden; display: none;}
    header {visibility: hidden; display: none;}
    .stAppDeployButton {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    /* Ajuste Mobile */
    .stApp { background-color: #FFFFFF; }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 8rem !important;
    }

    /* Input Fixo no rodapé */
    .stChatInput {
        position: fixed; bottom: 0; left: 0; width: 100% !important;
        padding: 1rem; background: white !important; z-index: 99999;
        border-top: 1px solid #eee;
    }
    
    /* Balões de Chat */
    .stChatMessage .st-emotion-cache-1p1m4ay, 
    .stChatMessage .st-emotion-cache-10trblm,
    div[data-testid="stChatMessageAvatar"] { display: none !important; }

    div[data-testid="stChatMessage"] {
        display: flex; width: 100%; background-color: transparent !important;
        padding: 0.3rem 0; border: none !important;
    }

    /* Assistente (Rosa) */
    div[data-testid="stChatMessage"]:nth-child(even) .stMarkdown {
        background-color: #E91E63 !important; color: #FFFFFF !important;
        text-align: left; border-radius: 20px 20px 20px 5px;
        padding: 12px 18px; max-width: 85%;
        box-shadow: 0 2px 5px rgba(233, 30, 99, 0.2);
    }
    div[data-testid="stChatMessage"]:nth-child(even) p { color: #FFFFFF !important; }

    /* Usuário (Cinza) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        flex-direction: row-reverse; justify-content: flex-end;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) .stMarkdown {
        background-color: #F2F2F7 !important; color: #333333 !important;
        text-align: right; border-radius: 20px 20px 5px 20px;
        padding: 12px 18px; max-width: 80%;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) p { color: #333333 !important; }

    /* Card de Produto */
    .product-card {
        background: white; border-radius: 12px; padding: 10px;
        margin-top: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
    prompt = f"Voce é Vendedor simpatico da Glumi. Estoque: {txt}. Cliente: '{pergunta}'. Responda curto. Finalize com [ID_DO_PRODUTO] se achar algo."
    
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
        st.markdown("<h3 style='text-align:center'>Glumi</h3>", unsafe_allow_html=True)

# Inicializa Chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! O que você procura?"}]

# Mostra Histórico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content_show = re.sub(r"\[.*?\]", "", msg["content"])
        st.markdown(content_show)

# Input do Usuário
if prompt := st.chat_input("Digite aqui..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# --- 7. RESPOSTA DA IA ---
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
                
                # LOGICA DO CARD (Corrigida)
                if id_prod:
                    row_df = df[df['id'] == id_prod] # Pega o DataFrame filtrado
                    if not row_df.empty:
                        r = row_df.iloc[0] # Pega a linha específica (Series)
                        
                        # Define HTML do Card
                        html_card = f"""
                        <div class="product-card">
                            <div class="prod-name">{r['nome']}</div>
                            <div class="prod-price">R$ {float(r['preco_venda']):,.2f}</div>
                            <div class="prod-id">Ref: {r['id']}</div>
                        </div>
                        """
                        
                        # Layout: Imagem na esquerda, Card na direita
                        col_img, col_txt = st.columns([1, 2])
                        
                        with col_img:
                            # CORREÇÃO DA IMAGEM AQUI
                            img_path = r['imagem_local'] # Usa 'r', não 'row'
                            
                            # Verifica se existe arquivo local
                            if pd.notna(img_path) and os.path.exists(str(img_path)):
                                st.image(str(img_path), use_container_width=True)
                            
                            # Se não, tenta URL da web
                            elif pd.notna(r.get('imagem_url')) and str(r['imagem_url']).startswith('http'):
                                st.image(str(r['imagem_url']), use_container_width=True)
                            
                            # Se falhar tudo
                            else:
                                st.write("📷") 

                        with col_txt:
                            st.markdown(html_card, unsafe_allow_html=True)

        # Salva resposta no histórico
        st.session_state.messages.append({"role": "assistant", "content": resp})
