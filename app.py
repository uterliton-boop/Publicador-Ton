import os
import streamlit as st
from openai import OpenAI
from weasyprint import HTML, CSS

st.set_page_config(page_title="Atlas Studio: Editora & Publicador 1-Click", page_icon="📚", layout="centered")

# Estilização Visual Avançada (Tema Editorial Moderno e Elegante)
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
    }
    .subtitle {
        text-align: center;
        color: #9ca3af;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 12px;
        padding: 12px 20px;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.5);
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #1e1b4b;
        color: #f3f4f6;
        border: 1px solid #312e81;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📚 Atlas Studio</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Editora e Estúdio Automatizado de Alta Densidade Literária</p>', unsafe_allow_html=True)

secret_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
api_key_input = st.text_input("🔑 Chave da API OpenAI (GPT-4o / DALL-E 3)", value=secret_key, type="password")

if api_key_input:
    client = OpenAI(api_key=api_key_input)
else:
    st.warning("⚠️ Insira a sua chave da API da OpenAI para continuar.")

modo = st.radio("Selecione o Fluxo de Trabalho:", ["📝 Gerar Obra Consistente (12 Capítulos / 10 Subpartes)", "📁 Enviar Manuscrito Existente (.docx)"])
st.markdown("---")

if modo == "📝 Gerar Obra Consistente (12 Capítulos / 10 Subpartes)":
    st.subheader("⚙️ Configuração e Identidade da Obra")
    
    titulo_livro = st.text_input("Título do Livro", "O Peso do Silêncio e das Estrelas")
    nome_autor = st.text_input("Nome do Autor", "Uterliton Araujo Silva")
    nome_protagonista = st.text_input("Nome do Protagonista Principal (Trava de Identidade)", "Clara")
    genero = st.selectbox("Gênero Literário", ["Romance Filosófico / Épico", "Desenvolvimento Pessoal / Filosofia Profunda", "Drama Psicológico Intenso"])
    ideia_central = st.text_area("Premisa e Enredo Geral", "Uma obra monumental sobre escolhas, o peso do tempo, a vulnerabilidade e a descoberta interior.")
    tom_voz = st.selectbox("Tom de Voz", ["Contemplativo, extremamente detalhado, filosófico e imersivo", "Dramático, poético e analítico"])

    # Estados da sessão para persistência
    if "capitulos_texto" not in st.session_state:
        st.session_state.capitulos_texto = {}
    if "sumario_lista" not in st.session_state:
        st.session_state.sumario_lista = []
    if "livro_revisado" not in st.session_state:
        st.session_state.livro_revisado = False
    if "capas_geradas" not in st.session_state:
        st.session_state.capas_geradas = []

    # BOTÃO 1: Escrever Obra
    if st.button("🚀 1. Escrever Obra com Protagonista Único (12 Capítulos)"):
        if not api_key_input:
            st.error("Insira a Chave da API.")
        elif not nome_protagonista:
            st.error("Por favor, preencha o nome do protagonista.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("Passo 1: Criando arquitetura de 12 capítulos...")
                progress_bar.progress(2)
                
                prompt_est = f"Crie um sumário exato de 12 títulos de capítulos coesos e progressivos para o livro '{titulo_livro}' ({genero}), centrado na jornada de {nome_protagonista}. Retorne apenas os 12 títulos, um por linha, numerados."
                res_est = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_est}], temperature=0.7)
                capitulos_limpos = [c.strip() for c in res_est.choices[0].message.content.split("\n") if c.strip()][:12]
                st.session_state.sumario_lista = capitulos_limpos

                st.session_state.capitulos_texto = {}
                total_caps = len(capitulos_limpos)
                total_etapas = total_caps * 10
                etapa_atual = 0

                for i, cap_titulo in enumerate(capitulos_limpos, 1):
                    texto_completo_capitulo = f"<h2>{cap_titulo}</h2>\n"
                    contexto_sub = f"Início do capítulo {cap_titulo} com a protagonista {nome_protagonista}."

                    for sub in range(1, 11):
                        etapa_atual += 1
                        porcentagem = int(5 + (etapa_atual / total_etapas) * 85)
                        progress_bar.progress(min(porcentagem, 95))
                        status_text.text(f"Escrevendo Capítulo {i}/12 (Subparte {sub}/10) - Focado em {nome_protagonista}...")

                        prompt_sub = f"""
                        Escreva a Subparte {sub} de 10 do Capítulo {i} ({cap_titulo}) para o livro '{titulo_livro}', de {nome_autor}.
                        REGRAS ABSOLUTAS DE CONTINUIDADE E IDENTIDADE (OBRIGATÓRIO):
                        - A ÚNICA E EXCLUSIVA protagonista desta história deve ser '{nome_protagonista}'. NUNCA mude o nome para outro. É sempre '{nome_protagonista}' do início ao fim.
                        - Mantenha absoluta consistência com os acontecimentos anteriores.
                        - Desenvolva diálogos profundos, descrições ricas e reflexões psicológicas aprofundadas. Esta subparte deve ser longa.
                        - Contexto do trecho anterior: {contexto_sub[-500:]}
                        - Tom: {tom_voz}.
                        - Formatação: Retorne estritamente em HTML limpo usando tags <p> para os parágrafos. Nunca use blocos de código ```html.
                        """

                        res_s = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt_sub}],
                            temperature=0.75,
                            max_tokens=4000
                        )
                        conteudo_sub = res_s.choices[0].message.content
                        texto_completo_capitulo += f"\n{conteudo_sub}\n"
                        contexto_sub += f" | {conteudo_sub[-300:]}"

                    st.session_state.capitulos_texto[i] = texto_completo_capitulo

                progress_bar.progress(100)
                status_text.text("✅ Obra gerada com identidade e protagonista fixos!")
                st.session_state.livro_revisado = False
                st.rerun()

            except Exception as e:
                st.error(f"Erro na geração: {e}")

    if st.session_state.capitulos_texto:
        st.success(f"📚 Obra carregada na memória com capítulos consistentes focados em {nome_protagonista}.")
        
        st.markdown("---")
        st.subheader("🎨 2. Estúdio de Capas por IA")
        
        if st.button("Gerar 3 Opções de Capa com DALL-E 3"):
            if not api_key_input:
                st.error("Insira a Chave da API.")
            else:
                status_capa = st.empty()
                status_capa.text("Gerando capas artísticas de alto padrão...")
                
                try:
                    prompt_base_capa = f"Professional book cover design for a {genero} book titled '{titulo_livro}', inspired by: {ideia_central}. Artistic, high quality, typography space, elegant composition."
                    
                    imagens_urls = []
                    for k in range(3):
                        variacoes = [
                            f"{prompt_base_capa} Cinematic lighting, dramatic atmosphere.",
                            f"{prompt_base_capa} Minimalist editorial style, symbolic and profound.",
                            f"{prompt_base_capa} Fine art book cover design, deep philosophical mood."
                        ]
                        response_img = client.images.generate(
                            model="dall-e-3",
                            prompt=variacoes[k],
                            size="1024x1024",
                            quality="standard",
                            n=1,
                        )
                        imagens_urls.append(response_img.data[0].url)
                    
                    st.session_state.capas_geradas = imagens_urls
                    status_capa.text("✅ 3 opções de capas geradas com sucesso!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao gerar capas: {e}")

        if st.session_state.capas_geradas:
            st.write("### Escolha a sua capa favorita:")
            cols = st.columns(3)
            for idx, img_url in enumerate(st.session_state.capas_geradas):
                with cols[idx]:
                    st.image(img_url, caption=f"Opção {idx+1}", use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 3. Revisão Literária e Padronização")
        
        if st.button("Revisar Manuscrito e Garantir Nome Único"):
            status_rev = st.empty()
            prog_rev = st.progress(0)
            
            try:
                status_rev.text(f"Padronizando o nome '{nome_protagonista}' em todo o livro...")
                total_c = len(st.session_state.capitulos_texto)
                
                for i in range(1, total_c + 1):
                    prog_rev.progress(int((i / total_c) * 100))
                    texto_atual = st.session_state.capitulos_texto[i]
                    
                    prompt_rev = f"""
                    Faça uma revisão literária rigorosa neste capítulo. Certifique-se de que a protagonista seja estritamente chamada de '{nome_protagonista}'. Elimine repetições e pola a fluidez. Retorne apenas o HTML revisado (mantendo <h2> e <p>):
                    {texto_atual}
                    """
                    res_r = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt_rev}],
                        temperature=0.3,
                        max_tokens=4000
                    )
                    st.session_state.capitulos_texto[i] = res_r.choices[0].message.content

                prog_rev.progress(100)
                status_rev.text("✅ Revisão e padronização concluídas!")
                st.session_state.livro_revisado = True
                st.rerun()

            except Exception as e:
                st.error(f"Erro na revisão: {e}")

        if st.session_state.livro_revisado:
            st.info("✨ Manuscrito revisado com consistência absoluta.")

        st.markdown("---")
        st.subheader("📥 4. Diagramação e Exportação do PDF")
        
        modelo_diagramacao = st.selectbox(
            "Escolha o Estilo de Diagramação:",
            [
                "📖 Clássico Literário (Times New Roman, recuo elegante)",
                "🖋️ Moderno Minimalista (Fonte limpa, respiro amplo)",
                "📜 Épico / Acadêmico (Margens robustas, tom aristocrático)"
            ]
        )

        if st.button("Gerar PDF Final Perfeito"):
            status_pdf = st.empty()
            status_pdf.text("Renderizando PDF editorial final...")
            
            try:
                if "Clássico Literário" in modelo_diagramacao:
                    css_fonte = "'Times New Roman', serif"
                    css_tamanho = "10pt"
                    css_linha = "1.45"
                    css_recuo = "6mm"
                elif "Moderno Minimalista" in modelo_diagramacao:
                    css_fonte = "Helvetica, Arial, sans-serif"
                    css_tamanho = "9.5pt"
                    css_linha = "1.6"
                    css_recuo = "4mm"
                else:
                    css_fonte = "'Georgia', serif"
                    css_tamanho = "10.5pt"
                    css_linha = "1.5"
                    css_recuo = "8mm"

                sumario_html = "<h1>Sumário</h1>\n<ul style='list-style: none; padding: 0; line-height: 1.8;'>\n"
                for idx, titulo_cap in enumerate(st.session_state.sumario_lista, 1):
                    sumario_html += f"<li><b>Capítulo {idx}:</b> {titulo_cap.split('. ', 1)[-1]}</li>\n"
                sumario_html += "</ul>\n<div class='page-break'></div>\n"

                corpo_caps = ""
                for i in range(1, len(st.session_state.capitulos_texto) + 1):
                    corpo_caps += f"<div class='chapter'>\n{st.session_state.capitulos_texto[i]}\n</div>\n<div class='page-break'></div>\n"

                html_final = f"""
                <!DOCTYPE html>
                <html lang="pt">
                <head>
                    <meta charset="UTF-8">
                    <style>
                        @page {{
                            size: A5;
                            margin: 25mm 20mm 25mm 20mm;
                            @bottom-right {{
                                content: counter(page);
                                font-family: {css_fonte};
                                font-size: 9pt;
                            }}
                        }}
                        body {{
                            font-family: {css_fonte};
                            font-size: {css_tamanho};
                            line-height: {css_linha};
                            word-spacing: 0.8px;
                            letter-spacing: 0.1px;
                            text-align: justify;
                            color: #1a1a1a;
                        }}
                        h1 {{
                            text-align: center;
                            font-size: 22pt;
                            margin-top: 45mm;
                            margin-bottom: 15mm;
                            font-weight: normal;
                        }}
                        .author-cover {{
                            text-align: center;
                            font-size: 13pt;
                            font-style: italic;
                            margin-top: 5mm;
                            color: #444;
                        }}
                        h2 {{
                            font-size: 12.5pt;
                            margin-top: 15mm;
                            margin-bottom: 8mm;
                            page-break-before: always;
                            font-weight: bold;
                            color: #222;
                        }}
                        p {{
                            margin-bottom: 7pt;
                            text-indent: {css_recuo};
                            orphans: 3;
                            widows: 3;
                        }}
                        .page-break {{
                            page-break-after: always;
                        }}
                        .chapter {{
                            margin-bottom: 10mm;
                        }}
                    </style>
                </head>
                <body>
                    <h1>{titulo_livro}</h1>
                    <div class="author-cover">{nome_autor}</div>
                    <div class="page-break"></div>
                    
                    {sumario_html}
                    
                    {corpo_caps}
                    
                    <div class="page-break"></div>
                    <h2>Sobre o Autor</h2>
                    <p>{nome_autor} é escritor e observador atento das dinâmicas invisíveis do comportamento humano, investigando temas complexos com uma abordagem estética, filosófica e imersiva.</p>
                </body>
                </html>
                """

                pdf_filename = "livro_atlas_studio.pdf"
                HTML(string=html_final).write_pdf(pdf_filename)
                
                status_pdf.text("✅ PDF gerado com sucesso!")
                
                with open(pdf_filename, "rb") as f:
                    st.download_button(
                        label="📥 Baixar Livro em PDF (Atlas Studio)",
                        data=f,
                        file_name=f"{titulo_livro.replace(' ', '_')}_AtlasStudio.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")

else:
    st.info("Modo de upload de manuscrito `.docx` ativo.")
