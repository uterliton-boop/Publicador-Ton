import streamlit as st
import os
from docx import Document
from openai import OpenAI
from PIL import Image
from weasyprint import HTML, CSS
from pypdf import PdfReader

# Configuração da Página do App no Celular
st.set_page_config(page_title="Publicador Mobile 1-Click", page_icon="📚", layout="centered")

st.title("📚 Publicador Mobile 1-Click")
st.write("Transforme seu manuscrito em um livro pronto para gráfica direto pelo celular.")

# ==========================================
# CAMPOS DE ENTRADA (INTERFACE MOBILE)
# ==========================================
api_key_input = st.text_input("Chave da API OpenAI (GPT-4o)", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
titulo = st.text_input("Título do Livro", "Meu Livro Incrível")
autor = st.text_input("Nome do Autor", "Seu Nome")

arquivo_docx = st.file_uploader("Envie o Manuscrito (.docx - 200 a 300 páginas)", type=["docx"])
arquivo_capa = st.file_uploader("Envie a Imagem da Capa (Frente - Alta Resolução)", type=["jpg", "png"])

if st.button("🚀 Processar e Gerar Livro Completo", type="primary"):
    if not api_key_input or not arquivo_docx or not arquivo_capa:
        st.error("Por favor, preencha a chave da API e envie os arquivos necessários.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            os.makedirs("dist", exist_ok=True)
            client = OpenAI(api_key=api_key_input)
            
            # 1. Ler texto do Word
            status_text.text("📖 Lendo o arquivo do manuscrito...")
            doc = Document(arquivo_docx)
            progress_bar.progress(15)
            
            # 2. Revisão por Blocos/Capítulos (Suporta livros longos)
            status_text.text("🤖 Executando revisão literária em 4 camadas (Capítulo por Capítulo)...")
            
            html_total = ""
            linhas_capitulo = []
            
            def processar_bloco_ia(texto_bloco):
                if not texto_bloco.strip():
                    return ""
                prompt = f"""
                Atue como um Editor Sênior de livros. Revise o texto abaixo aplicando:
                1. Correção ortográfica e gramatical rigorosa (Acordo Ortográfico).
                2. Eliminação de vícios de linguagem e repetições próximas.
                3. Padronização de diálogos com travessões (—).
                Mantenha o tom do autor. Retorne apenas em HTML limpo (<p>, <h2>).
                
                Texto:
                {texto_bloco}
                """
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response.choices[0].message.content

            total_paragrafos = len(doc.paragraphs)
            for i, p in enumerate(doc.paragraphs):
                texto = p.text.strip()
                if not texto:
                    continue
                
                if p.style.name.startswith('Heading') or "capítulo" in texto.lower() or "chapter" in texto.lower():
                    if linhas_capitulo:
                        bloco_texto = "\n".join(linhas_capitulo)
                        html_total += processar_bloco_ia(bloco_texto)
                        linhas_capitulo = []
                    html_total += f"<h2>{texto}</h2>"
                else:
                    linhas_capitulo.append(texto)
                    if len("\n".join(linhas_capitulo)) > 15000:
                        bloco_texto = "\n".join(linhas_capitulo)
                        html_total += processar_bloco_ia(bloco_texto)
                        linhas_capitulo = []
            
            if linhas_capitulo:
                bloco_texto = "\n".join(linhas_capitulo)
                html_total += processar_bloco_ia(bloco_texto)
                
            progress_bar.progress(55)
            
            # 3. Diagramar Miolo
            status_text.text("📑 Diagramando o miolo do livro...")
            css_editorial = """
            @page {
                size: 140mm 210mm;
                margin: 20mm 15mm 20mm 20mm;
                @bottom-center { content: counter(page); font-family: serif; font-size: 10pt; }
            }
            body { font-family: 'Georgia', serif; font-size: 11pt; line-height: 1.4; text-align: justify; hyphens: auto; }
            p { text-indent: 1.5em; margin: 0; orphans: 2; widows: 2; }
            h2 { page-break-before: always; text-align: center; margin-top: 30%; margin-bottom: 2em; }
            """
            
            html_completo = f"<html><body><div style='text-align:center; margin-top:40%;'><h1>{titulo}</h1><h3>{autor}</h3></div>{html_total}</body></html>"
            path_miolo = "dist/miolo.pdf"
            HTML(string=html_completo).write_pdf(path_miolo, stylesheets=[CSS(string=css_editorial)])
            
            reader = PdfReader(path_miolo)
            num_paginas = len(reader.pages)
            progress_bar.progress(80)
            
            # 4. Calcular Lombada e Gerar Capa 300 DPI
            status_text.text(f"🎨 Calculando lombada para {num_paginas} páginas e gerando capa...")
            calibre_papel = 0.116
            lombada_mm = (num_paginas / 2) * calibre_papel
            
            DPI = 300
            mm_to_px = lambda mm: int((mm / 25.4) * DPI)
            largura_total_mm = 80 + 140 + lombada_mm + 140 + 80 + 6
            altura_total_mm = 210 + 6
            
            capa_img = Image.open(arquivo_capa)
            capa_aberta = Image.new('RGB', (mm_to_px(largura_total_mm), mm_to_px(altura_total_mm)), color=(255, 255, 255))
            capa_aberta.paste(capa_img.resize((mm_to_px(140), mm_to_px(210))), (mm_to_px(80 + 140 + lombada_mm), mm_to_px(3)))
            
            path_capa = "dist/capa_300dpi.pdf"
            capa_aberta.save(path_capa, "PDF", resolution=300.0)
            
            progress_bar.progress(100)
            status_text.text("🎉 Processo concluído com sucesso!")
            st.success(f"Livro gerado com {num_paginas} páginas!")
            
            # Botões de Download
            with open(path_miolo, "rb") as f:
                st.download_button("📥 Baixar PDF do Miolo", f, file_name="miolo.pdf", mime="application/pdf")
            
            with open(path_capa, "rb") as f:
                st.download_button("📥 Baixar PDF da Capa (300 DPI)", f, file_name="capa.pdf", mime="application/pdf")

        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {e}")
