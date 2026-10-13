import html
import io
import re
import unicodedata
from pathlib import Path

import streamlit as st
from openai import OpenAI
from weasyprint import HTML
from docx import Document

st.set_page_config(
    page_title="Publicador Editorial",
    page_icon="📚",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stApp { background: #10131a; }
    .stButton > button, .stDownloadButton > button {
        width: 100%; font-weight: 650; border-radius: 8px;
    }
    div[data-testid="stProgressBar"] > div > div { background-color: #b88a44; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📚 Publicador Editorial")
st.caption("Preparação de manuscritos e geração de miolo em PDF para revisão editorial.")

st.info(
    "Este aplicativo prepara um miolo em PDF. Ele não substitui revisão literária, "
    "revisão ortográfica profissional, prova impressa ou validação das exigências "
    "específicas da gráfica/plataforma."
)

def safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value[:90] or "livro"

def text_to_html_paragraphs(text: str) -> str:
    """Converte texto simples em HTML seguro; não confia em HTML gerado pela IA."""
    chunks = re.split(r"\n\s*\n", text.strip())
    result = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        # Linhas curtas sem pontuação final podem funcionar como intertítulos.
        if len(lines) == 1 and len(lines[0]) <= 90 and not re.search(r"[.!?…]$", lines[0]):
            result.append(f"<h3>{html.escape(lines[0])}</h3>")
        else:
            paragraph = " ".join(lines)
            result.append(f"<p>{html.escape(paragraph)}</p>")
    return "\n".join(result)

def build_book_html(title: str, author: str, chapters: list[dict], bio: str) -> str:
    title_safe = html.escape(title)
    author_safe = html.escape(author)
    bio_html = text_to_html_paragraphs(bio)
    toc_items = []
    chapter_sections = []

    for i, chapter in enumerate(chapters, 1):
        chapter_id = f"capitulo-{i}"
        chapter_title = html.escape(chapter["title"])
        toc_items.append(
            f'<li><a href="#{chapter_id}"><span>Capítulo {i} — {chapter_title}</span>'
            f'<span class="page-number"></span></a></li>'
        )
        chapter_sections.append(
            f'<section class="chapter" id="{chapter_id}">'
            f'<h2>Capítulo {i}<span class="chapter-title">{chapter_title}</span></h2>'
            f'{text_to_html_paragraphs(chapter["text"])}'
            f'</section>'
        )

    chapters_html = "\n".join(chapter_sections)
    toc_html = "\n".join(toc_items)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{title_safe}</title>
<style>
@page {{
    size: A5;
    margin: 20mm 18mm 20mm 22mm;
    @bottom-center {{
        content: counter(page);
        font-family: "Liberation Serif", "DejaVu Serif", serif;
        font-size: 9pt;
        color: #555;
    }}
}}
@page:first {{ @bottom-center {{ content: ""; }} }}
* {{ box-sizing: border-box; }}
body {{
    font-family: "Liberation Serif", "DejaVu Serif", serif;
    font-size: 10.5pt;
    line-height: 1.48;
    color: #191919;
    text-align: justify;
    hyphens: auto;
}}
.cover {{
    page-break-after: always;
    min-height: 205mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
}}
.cover h1 {{
    font-size: 26pt;
    line-height: 1.18;
    font-weight: normal;
    text-align: center;
    margin: 0 0 22mm;
}}
.cover .author {{
    font-size: 13pt;
    letter-spacing: .5px;
}}
.toc {{ page-break-after: always; }}
.toc h1 {{
    font-size: 18pt;
    text-align: center;
    font-weight: normal;
    margin: 0 0 12mm;
}}
.toc ul {{ list-style: none; margin: 0; padding: 0; }}
.toc li {{ margin: 0 0 7mm; }}
.toc a {{
    color: inherit;
    text-decoration: none;
    display: flex;
    align-items: baseline;
    gap: 4mm;
}}
.toc a::after {{
    content: leader(".") " " target-counter(attr(href), page);
    flex: 1;
}}
.chapter {{ page-break-before: always; }}
.chapter h2 {{
    font-size: 16pt;
    line-height: 1.25;
    text-align: center;
    font-weight: normal;
    margin: 0 0 12mm;
    page-break-after: avoid;
}}
.chapter-title {{ display: block; font-weight: bold; margin-top: 4mm; }}
h3 {{
    font-size: 11pt;
    text-align: left;
    margin: 7mm 0 3mm;
    page-break-after: avoid;
}}
p {{
    margin: 0 0 3.2mm;
    text-indent: 7mm;
    orphans: 3;
    widows: 3;
}}
p + h3 {{ margin-top: 7mm; }}
.author-bio {{ page-break-before: always; }}
.author-bio h2 {{
    font-size: 16pt; text-align: center; font-weight: normal; margin-bottom: 10mm;
}}
</style>
</head>
<body>
<div class="cover">
    <h1>{title_safe}</h1>
    <div class="author">{author_safe}</div>
</div>
<nav class="toc">
    <h1>Sumário</h1>
    <ul>{toc_html}</ul>
</nav>
{chapters_html}
<section class="author-bio">
    <h2>Sobre o autor</h2>
    {bio_html}
</section>
</body>
</html>"""

def extract_docx(uploaded_file):
    document = Document(uploaded_file)
    blocks = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if "heading 1" in style_name or "título 1" in style_name or "titulo 1" in style_name:
            blocks.append(("heading", text))
        else:
            blocks.append(("text", text))

    chapters = []
    current = None
    intro = []
    for kind, text in blocks:
        if kind == "heading":
            if current:
                chapters.append(current)
            current = {"title": text, "text": ""}
        elif current:
            current["text"] += text + "\n\n"
        else:
            intro.append(text)

    if current:
        chapters.append(current)

    if not chapters:
        all_text = "\n\n".join(text for _, text in blocks)
        chapters = [{"title": "Manuscrito", "text": all_text}]
    elif intro:
        chapters.insert(0, {"title": "Texto introdutório", "text": "\n\n".join(intro)})

    return chapters

def get_api_key():
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""

with st.sidebar:
    st.header("Configurações")
    st.caption("Conecte a API para criar livros com inteligência artificial.")

    # A chave pode vir dos segredos do Streamlit ou ser digitada nesta sessão.
    # O campo não grava a chave em arquivo nem a exibe por padrão.
    show_api_key = st.checkbox("Mostrar chave da API", value=False)
    api_key = st.text_input(
        "Chave da API OpenAI",
        value=get_api_key(),
        type="default" if show_api_key else "password",
        key="openai_api_key_input",
        placeholder="Cole sua chave da API aqui",
        help=(
            "A chave fica oculta por padrão. Para uso publicado, prefira configurar "
            "OPENAI_API_KEY nos Secrets do Streamlit; não compartilhe sua chave."
        ),
    )
    if api_key.strip():
        st.caption("✓ Chave preenchida — ainda será validada pela API ao gerar o livro.")
    else:
        st.caption("Nenhuma chave informada. A conversão de DOCX para PDF continua disponível.")

    model = st.selectbox("Modelo", ["gpt-4o-mini", "gpt-4o"], index=0)
    st.caption("A utilização da API é cobrada separadamente da assinatura do ChatGPT.")

mode = st.radio(
    "Como deseja começar?",
    ["Criar livro com IA", "Preparar manuscrito .docx"],
    horizontal=False,
)

if mode == "Criar livro com IA":
    st.subheader("Projeto editorial")
    title = st.text_input("Título do livro", "O Alaúde e a Sabedoria dos Reinos")
    author = st.text_input("Nome do autor", "Uterliton Araujo Silva")
    genre = st.selectbox(
        "Gênero",
        [
            "Fantasia épica / romance filosófico",
            "Romance literário",
            "Desenvolvimento pessoal / filosofia prática",
            "Mistério / suspense",
            "Ficção histórica",
        ],
    )
    premise = st.text_area(
        "Premissa ou sinopse",
        "Uma jornada de autoconhecimento, o som de um alaúde místico e as lições guardadas nos reinos antigos.",
        height=120,
    )
    tone = st.selectbox(
        "Tom de voz",
        [
            "Contemplativo, poético e reflexivo",
            "Dramático e envolvente",
            "Clássico, atmosférico e misterioso",
            "Direto, acessível e prático",
        ],
    )
    chapter_count = st.slider("Número de capítulos", 4, 20, 12)
    target_words = st.slider("Meta aproximada de palavras por capítulo", 800, 3000, 1800, step=200)
    bio = st.text_area(
        "Biografia do autor",
        "Uterliton Araujo Silva escreve sobre imaginação, comportamento humano e busca de sentido. Sua obra convida o leitor à reflexão e à descoberta de novas perspectivas.",
        height=100,
    )

    if st.button("Gerar manuscrito e PDF", type="primary"):
        if not api_key or not api_key.strip():
            st.error("Insira a chave da API ou configure OPENAI_API_KEY nos segredos do Streamlit.")
            st.stop()
        if not title.strip() or not author.strip() or not premise.strip():
            st.error("Preencha o título, o nome do autor e a premissa.")
            st.stop()

        client = OpenAI(api_key=api_key.strip())
        progress = st.progress(0)
        status = st.empty()

        try:
            status.write("1/3 — Planejando a estrutura...")
            outline_prompt = f"""
Você é um editor e arquiteto de narrativas em língua portuguesa.
Crie exatamente {chapter_count} títulos de capítulos para o livro "{title}".
Gênero: {genre}.
Premissa: {premise}
Tom: {tone}.
Garanta progressão lógica, variedade entre capítulos e um desfecho coerente.
Responda somente com uma lista numerada, um título por linha. Não inclua introdução.
"""
            outline_response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Você é um editor literário experiente. Escreva em português brasileiro."},
                    {"role": "user", "content": outline_prompt},
                ],
                temperature=0.6,
            )
            outline_text = outline_response.choices[0].message.content or ""
            titles = []
            for line in outline_text.splitlines():
                cleaned = re.sub(r"^\s*(?:capítulo\s*)?\d+[\s.)\-:]*", "", line, flags=re.I).strip()
                cleaned = cleaned.strip("*# \t")
                if cleaned:
                    titles.append(cleaned)
            titles = titles[:chapter_count]
            if len(titles) < chapter_count:
                st.error(f"A IA retornou apenas {len(titles)} títulos. Tente novamente.")
                st.stop()

            chapters = []
            continuity_notes = "Ainda não há acontecimentos anteriores."
            for i, chapter_title in enumerate(titles, 1):
                status.write(f"2/3 — Escrevendo capítulo {i} de {len(titles)}...")
                progress.progress(int((i / len(titles)) * 75))

                chapter_prompt = f"""
Escreva o capítulo {i} de {chapter_count} do livro "{title}", de {author}.
Gênero: {genre}.
Premissa: {premise}
Tom: {tone}.
Título do capítulo: {chapter_title}
Meta: aproximadamente {target_words} palavras. Se não for possível atingir a meta numa resposta,
priorize uma narrativa completa, coerente e bem desenvolvida; não repita ideias para aumentar volume.
Continuidade já estabelecida:
{continuity_notes}

Diretrizes:
- Escreva em português brasileiro natural, com qualidade literária e ritmo variado.
- Desenvolva cenas, personagens, conflitos e consequências concretas; evite generalidades e repetições.
- Mantenha consistência de nomes, motivações, cronologia e ambientação.
- Não invente citações de autores reais nem apresente fatos históricos duvidosos como certos.
- Não inclua comentários sobre o processo de escrita, notas para o editor ou instruções ao leitor.
- Entregue somente o texto do capítulo, sem HTML e sem bloco Markdown.
"""
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Você é um romancista e editor profissional. Preserve continuidade e escreva em português brasileiro."},
                        {"role": "user", "content": chapter_prompt},
                    ],
                    temperature=0.75,
                    max_tokens=5000,
                )
                chapter_text = (response.choices[0].message.content or "").strip()
                if not chapter_text:
                    raise RuntimeError(f"O capítulo {i} voltou vazio.")
                chapters.append({"title": chapter_title, "text": chapter_text})

                # Resumo curto usado como memória narrativa para o próximo capítulo.
                summary_prompt = f"""
Resuma em até 140 palavras os acontecimentos, personagens presentes, decisões,
informações reveladas e ganchos deste capítulo. Não acrescente fatos.
Título: {chapter_title}
Texto:
{chapter_text}
"""
                summary_response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.2,
                    max_tokens=250,
                )
                summary = (summary_response.choices[0].message.content or "").strip()
                continuity_notes = (continuity_notes + "\n" + f"Capítulo {i} — {chapter_title}: {summary}")[-10000:]

            status.write("3/3 — Diagramando o PDF...")
            progress.progress(88)
            book_html = build_book_html(title, author, chapters, bio)
            pdf_bytes = HTML(string=book_html, base_url=".").write_pdf()
            progress.progress(100)
            status.success("PDF criado. Revise o manuscrito antes de publicar.")

            st.download_button(
                "📥 Baixar miolo em PDF",
                data=pdf_bytes,
                file_name=f"{safe_filename(title)}_miolo.pdf",
                mime="application/pdf",
                type="primary",
            )

            with st.expander("Prévia do sumário e dos capítulos"):
                for idx, chapter in enumerate(chapters, 1):
                    st.markdown(f"**Capítulo {idx} — {chapter['title']}**")
                    st.write(chapter["text"][:900] + ("…" if len(chapter["text"]) > 900 else ""))

            st.warning(
                "Antes de publicar, confira a contagem de palavras, revise o texto, valide os números "
                "do sumário no PDF e solicite uma prova de impressão. A paginação e as exigências "
                "podem variar conforme a gráfica ou plataforma."
            )

        except Exception as exc:
            # Mensagens mais claras para erros comuns da API; detalhes técnicos continuam disponíveis.
            if exc.__class__.__name__ == "AuthenticationError":
                st.error("A OpenAI recusou a chave informada. Confira se ela está correta e ativa.")
            elif exc.__class__.__name__ == "RateLimitError":
                st.error("A API recusou a solicitação por limite ou saldo. Confira o faturamento e os limites da API.")
            else:
                st.error(f"Não foi possível concluir a geração: {exc}")
            st.caption("Confira a chave, o faturamento/créditos da API, o modelo escolhido e as dependências instaladas.")

else:
    st.subheader("Preparar manuscrito existente")
    uploaded = st.file_uploader("Envie seu arquivo Word (.docx)", type=["docx"])
    doc_title = st.text_input("Título do livro", "Meu Livro")
    doc_author = st.text_input("Nome do autor", "Nome do Autor")
    doc_bio = st.text_area("Biografia do autor", "Escreva aqui uma breve biografia do autor.")
    st.caption(
        "O importador usa os estilos de título do Word para identificar capítulos. "
        "Se o manuscrito não tiver títulos formatados como 'Título 1' / 'Heading 1', "
        "o conteúdo poderá ser importado como uma única seção."
    )

    if uploaded is not None:
        if st.button("Converter manuscrito para PDF", type="primary"):
            try:
                chapters = extract_docx(uploaded)
                if not chapters or not any(ch.get("text", "").strip() for ch in chapters):
                    st.error("Não encontrei texto utilizável no arquivo.")
                    st.stop()
                pdf_bytes = HTML(
                    string=build_book_html(doc_title, doc_author, chapters, doc_bio),
                    base_url=".",
                ).write_pdf()
                st.success(f"Manuscrito preparado: {len(chapters)} seção(ões) identificada(s).")
                st.download_button(
                    "📥 Baixar PDF diagramado",
                    data=pdf_bytes,
                    file_name=f"{safe_filename(doc_title)}_miolo.pdf",
                    mime="application/pdf",
                    type="primary",
                )
                st.warning(
                    "Esta conversão preserva o texto e reconhece títulos básicos, mas não reproduz "
                    "fielmente todos os elementos do Word, como imagens, tabelas, notas de rodapé, "
                    "ornamentos e estilos complexos. Faça uma conferência completa do PDF."
                )
            except Exception as exc:
                st.error(f"Falha ao importar ou converter o DOCX: {exc}")
