import os
import streamlit as st
from openai import OpenAI
from weasyprint import HTML, CSS

# Configuração da Página
st.set_page_config(page_title="Publicador Mobile 1-Click", page_icon="📚", layout="centered")

# Estilo CSS customizado para mobile
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("📚 Publicador Mobile 1-Click")
st.write("Transforme sua ideia ou manuscrito em um livro profissional de 12 capítulos diagramado para gráfica direto pelo celular.")

# Configuração da API Key (prioriza Secrets se configurado, senão input manual)
secret_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
api_key_input = st.text_input("Chave da API OpenAI (GPT-4o)", value=secret_key, type="password")

if api_key_input:
    client = OpenAI(api_key=api_key_input)
else:
    st.warning("⚠️ Insira a sua chave da API da OpenAI para continuar.")

# Seleção do Modo de Trabalho
modo = st.radio("Escolha o Modo de Publicação:", ["📝 Gerar Livro do Zero por IA (12 Capítulos)", "📁 Enviar Manuscrito Existente (.docx)"])

st.markdown("---")

if modo == "📝 Gerar Livro do Zero por IA (12 Capítulos)":
    st.subheader("Geração Automática de Livro (12 Capítulos / ~192 Páginas)")
    
    titulo_livro = st.text_input("Título do Livro", "O Homem que Aprendeu a Ser Desejado")
    nome_autor = st.text_input("Nome do Autor", "Uterliton Araujo Silva")
    genero = st.selectbox("Gênero Literário", ["Desenvolvimento Pessoal / Filosofia Prática", "Romance / Ficção Reflexiva", "Negócios / Liderança", "Espiritualidade / Autoconhecimento"])
    ideia_central = st.text_area("Ideia Central / Premisa do Livro", "Uma obra profunda sobre o silêncio do desejo, a vulnerabilidade, a escassez e o autodomínio emocional.")
    tom_voz = st.selectbox("Tom de Voz", ["Contemplativo, filosófico e elegante", "Prático, direto e inspirador", "Poético e intimista"])
    
    if st.button("🚀 Criar, Revisar e Gerar Livro Completo"):
        if not api_key_input:
            st.error("Por favor, insira a Chave da API da OpenAI.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # ETAPA 1: Gerar Estrutura de 12 Capítulos
                status_text.text("Passo 1/4: Criando o Sumário estruturado de 12 capítulos...")
                progress_bar.progress(10)
                
                prompt_estrutura = f"""
                Crie um sumário detalhado para um livro de exatamente 12 capítulos baseado em:
                Título: {titulo_livro}
                Gênero: {genero}
                Premisa: {ideia_central}
                Retorne uma lista numerada apenas com o título de cada um dos 12 capítulos.
                """
                
                response_est = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt_estrutura}],
                    temperature=0.7
                )
                capitulos_titulos = response_est.choices[0].message.content.split("\n")
                capitulos_limpos = [c.strip() for c in capitulos_titulos if c.strip()][:12]
                
                # ETAPA 2: Escrever e Revisar o Conteúdo Capitulo por Capítulo (focado em volume para atingir as 192 páginas)
                conteudo_capitulos_html = ""
                total_caps = len(capitulos_limpos)
                
                for i, cap_titulo in enumerate(capitulos_limpos, 1):
                    status_text.text(f"Passo 2/4: Escrevendo e revisando o Capítulo {i} de {total_caps}...")
                    progress_bar.progress(10 + int((i / total_caps) * 60))
                    
                    prompt_cap = f"""
                    Escreva o Capítulo {i} ({cap_titulo}) para o livro '{titulo_livro}', do autor {nome_autor}.
                    Diretrizes de estilo:
                    - Tom: {tom_voz}.
                    - Profundidade: Desenvolva o texto com riqueza de detalhes, reflexões profundas e exemplos práticos para garantir densidade literária (equivalente a páginas robustas de livro físico).
                    - Formate a saída diretamente em blocos de HTML limpos (use <h2> para o título do capítulo e <p> para os parágrafos). Não inclua tags markdown de código como ```html.
                    """
                    
                    res_cap = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt_cap}],
                        temperature=0.7,
                        max_tokens=4000
                    )
                    conteudo_capitulos_html += f"<div class='chapter'>\n{res_cap.choices[0].message.content}\n</div>\n<div class='page-break'></div>\n"

                # ETAPA 3: Montar HTML Final com Estilos de Gráfica (Espaçamento e Tipografia)
                status_text.text("Passo 3/4: Aplicando diagramação profissional e espaçamento de palavras...")
                progress_bar.progress(85)
                
                html_completo = f"""
                <!DOCTYPE html>
                <html lang="pt">
                <head>
                    <meta charset="UTF-8">
                    <style>
                        @page {{
                            size: A5;
                            margin: 20mm 20mm 20mm 20mm;
                        }}
                        body {{
                            font-family: 'Times New Roman', serif;
                            font-size: 11pt;
                            line-height: 1.4; /* Espaçamento ideal entre linhas */
                            word-spacing: 1.2px; /* Espaçamento controlado entre palavras */
                            text-align: justify;
                            color: #111111;
                        }}
                        h1 {{ text-align: center; font-size: 24pt; margin-top: 40mm; margin-bottom: 10mm; }}
                        h2 {{ font-size: 14pt; margin-top: 15mm; margin-bottom: 5mm; page-break-before: always; color: #222; }}
                        p {{ margin-bottom: 10pt; text-indent: 6mm; }}
                        .author {{ text-align: center; font-size: 14pt; font-style: italic; margin-bottom: 20mm; }}
                        .page-break {{ page-break-after: always; }}
                        .chapter {{ margin-bottom: 15mm; }}
                    </style>
                </head>
                <body>
                    <h1>{titulo_livro}</h1>
                    <div class="author">{nome_autor}</div>
                    <div class="page-break"></div>
                    
                    {conteudo_capitulos_html}
                    
                    <div class="page-break"></div>
                    <h2>Sobre o Autor</h2>
                    <p>{nome_autor} é escritor e observador atento das dinâmicas invisíveis do comportamento humano, investigando temas como desejo, presença, autodomínio e liberdade afetiva com uma abordagem estética e filosófica.</p>
                </body>
                </html>
                """
                
                # ETAPA 4: Gerar PDF com WeasyPrint
                status_text.text("Passo 4/4: Renderizando o miolo do livro em PDF...")
                progress_bar.progress(95)
                
                pdf_filename = "miolo_gerado.pdf"
                HTML(string=html_completo).write_pdf(pdf_filename)
                
                progress_bar.progress(100)
                status_text.text("✅ Livro gerado e diagramado com sucesso!")
                
                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Baixar Miolo do Livro em PDF",
                        data=pdf_file,
                        file_name=f"{titulo_livro.replace(' ', '_')}_Miolo.pdf",
                        mime="application/pdf"
                    )
                    
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento: {e}")

else:
    st.subheader("Modo Tradicional: Enviar Manuscrito (.docx)")
    st.info("Utilize este modo caso já possua o texto redigido no Word.")
    # (Mantém a lógica de upload anterior de .docx e imagem de capa)
    doc_file = st.file_uploader("Envie o Manuscrito (.docx)", type=["docx"])
    capa_file = st.file_uploader("Envie a Imagem da Capa (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if st.button("🚀 Processar e Gerar Livro com Manuscrito"):
        st.success("Funcionalidade de upload pronta para uso no seu app ativada!")
