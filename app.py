
import html
import json
import re
import io
from pathlib import Path
from datetime import datetime

import streamlit as st
from openai import OpenAI
from weasyprint import HTML
from pypdf import PdfReader

# ==========================================================
# ATLAS STUDIO — EDITORA & PUBLICADOR
# ==========================================================

st.set_page_config(
    page_title="Atlas Studio | Publicador Editorial",
    page_icon="📚",
    layout="wide",
)

PASTA_PROJETOS = Path("atlas_projects")
PASTA_PROJETOS.mkdir(exist_ok=True)

# Preços de referência em USD por 1 milhão de tokens.
# Confira os valores atuais no site da OpenAI antes de usar.
PRECOS = {
    "gpt-4o-mini": {"entrada": 0.15, "saida": 0.60},
    "gpt-4o": {"entrada": 2.50, "saida": 10.00},
}


# ==========================================================
# FUNÇÕES DE APOIO
# ==========================================================

def nome_seguro(texto):
    texto = re.sub(r"[^\w-]+", "_", texto.strip(), flags=re.UNICODE)
    return texto.strip("_")[:80] or "projeto"


def contar_palavras(texto):
    return len(re.findall(r"\b[\wÀ-ÿ]+(?:[-'][\wÀ-ÿ]+)*\b", texto or ""))


def caminho_projeto(titulo):
    return PASTA_PROJETOS / f"{nome_seguro(titulo)}.json"


def salvar_projeto(projeto):
    """Salva primeiro em arquivo temporário para reduzir risco de corrupção."""
    projeto["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    destino = caminho_projeto(projeto["titulo"])
    temporario = destino.with_suffix(".tmp")

    temporario.write_text(
        json.dumps(projeto, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(destino)
    return destino


def carregar_projeto(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def calcular_custo(modelo, tokens_entrada, tokens_saida):
    preco = PRECOS[modelo]
    return (
        tokens_entrada * preco["entrada"]
        + tokens_saida * preco["saida"]
    ) / 1_000_000


def registrar_uso(projeto, uso, modelo):
    projeto.setdefault("uso", {
        "entrada": 0,
        "saida": 0,
        "custo_usd": 0.0,
    })

    projeto["uso"]["entrada"] += uso["entrada"]
    projeto["uso"]["saida"] += uso["saida"]

    projeto["uso"]["custo_usd"] = calcular_custo(
        modelo,
        projeto["uso"]["entrada"],
        projeto["uso"]["saida"],
    )


def chamada_ia(cliente, modelo, mensagens, temperatura=0.5,
               max_tokens=3000):
    resposta = cliente.chat.completions.create(
        model=modelo,
        messages=mensagens,
        temperature=temperatura,
        max_tokens=max_tokens,
    )

    texto = (resposta.choices[0].message.content or "").strip()
    uso_api = resposta.usage

    uso = {
        "entrada": uso_api.prompt_tokens if uso_api else 0,
        "saida": uso_api.completion_tokens if uso_api else 0,
    }

    return texto, uso


def extrair_titulos(texto, quantidade):
    titulos = []

    for linha in texto.splitlines():
        linha = re.sub(
            r"^\s*(?:cap[ií]tulo\s*)?\d+[\s.):\-]*",
            "",
            linha,
            flags=re.IGNORECASE,
        ).strip(" -*#\t")

        if linha:
            titulos.append(linha)

    return titulos[:quantidade]


def criar_pdf(titulo, autor, capitulos, biografia):
    """Escapa o texto para não interpretar conteúdo do manuscrito como HTML."""

    partes = []
    sumario = []

    for numero, capitulo in enumerate(capitulos, start=1):
        titulo_capitulo = html.escape(capitulo["titulo"])
        texto = capitulo["texto"]

        paragrafos = [
            p.strip()
            for p in re.split(r"\n\s*\n", texto)
            if p.strip()
        ]

        corpo = "".join(
            f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>"
            for p in paragrafos
        )

        partes.append(
            f'<section class="capitulo" id="capitulo-{numero}">'
            f"<h1>Capítulo {numero}</h1>"
            f"<h2>{titulo_capitulo}</h2>"
            f"{corpo}</section>"
        )

        sumario.append(
            f"<li>Capítulo {numero} — {titulo_capitulo}</li>"
        )

    bio_html = "".join(
        f"<p>{html.escape(p.strip())}</p>"
        for p in re.split(r"\n\s*\n", biografia or "")
        if p.strip()
    )

    titulo_html = html.escape(titulo)
    autor_html = html.escape(autor)

    documento = f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: 140mm 210mm;
            margin: 18mm 17mm 18mm 20mm;
            @bottom-center {{
                content: counter(page);
                font-size: 9pt;
            }}
        }}
        @page:first {{
            @bottom-center {{ content: ""; }}
        }}
        body {{
            font-family: "DejaVu Serif", serif;
            font-size: 10.5pt;
            line-height: 1.48;
            color: #171717;
        }}
        .capa {{
            page-break-after: always;
            height: 165mm;
            text-align: center;
            padding-top: 40mm;
        }}
        .capa h1 {{ font-size: 27pt; font-weight: normal; }}
        .autor {{ margin-top: 20mm; font-size: 13pt; }}
        .sumario {{ page-break-after: always; }}
        .sumario h1 {{
            text-align: center;
            font-size: 20pt;
            font-weight: normal;
        }}
        .sumario li {{ margin-bottom: 5mm; }}
        .capitulo {{ page-break-before: always; }}
        .capitulo h1 {{
            text-align: center;
            font-size: 12pt;
            font-weight: normal;
            text-transform: uppercase;
        }}
        .capitulo h2 {{
            text-align: center;
            font-size: 19pt;
            font-weight: normal;
            margin-bottom: 12mm;
            page-break-after: avoid;
        }}
        p {{
            margin: 0 0 3.2mm;
            text-indent: 7mm;
            orphans: 3;
            widows: 3;
        }}
        .biografia {{ page-break-before: always; }}
        .biografia h1 {{
            text-align: center;
            font-size: 18pt;
            font-weight: normal;
        }}
    </style>
    </head>
    <body>
        <section class="capa">
            <h1>{titulo_html}</h1>
            <div class="autor">{autor_html}</div>
        </section>

        <section class="sumario">
            <h1>Sumário</h1>
            <ul>{"".join(sumario)}</ul>
        </section>

        {"".join(partes)}

        <section class="biografia">
            <h1>Sobre o autor</h1>
            {bio_html}
        </section>
    </body>
    </html>
    """

    return HTML(string=documento).write_pdf()


def conferir_pdf(pdf_bytes, capitulos):
    """
    Estima a extensão dos capítulos usando o texto extraído do PDF.
    Não substitui a conferência visual da paginação.
    """
    leitor = PdfReader(io.BytesIO(pdf_bytes))
    paginas = [(p.extract_text() or "") for p in leitor.pages]
    inicios = {}

    for pagina, texto in enumerate(paginas):
        texto_normalizado = re.sub(r"\s+", " ", texto).casefold()

        for numero, capitulo in enumerate(capitulos, start=1):
            cabecalho = re.sub(
                r"\s+", " ",
                f"Capítulo {numero} {capitulo['titulo']}"
            ).casefold()

            if cabecalho in texto_normalizado:
                inicios.setdefault(numero, pagina)

    relatorio = []

    numeros = sorted(inicios)

    for pos, numero in enumerate(numeros):
        inicio = inicios[numero]

        if pos + 1 < len(numeros):
            fim = inicios[numeros[pos + 1]] - 1
        else:
            fim = len(paginas) - 1

        relatorio.append({
            "numero": numero,
            "titulo": capitulos[numero - 1]["titulo"],
            "paginas": max(0, fim - inicio + 1),
        })

    return len(paginas), relatorio


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

with st.sidebar:
    st.header("⚙️ Configurações")

    try:
        chave_padrao = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        chave_padrao = ""

    api_key = st.text_input(
        "Chave da API OpenAI",
        value=chave_padrao,
        type="password",
        placeholder="Cole sua chave aqui",
    )

    modelo = st.selectbox(
        "Modelo de texto",
        ["gpt-4o-mini", "gpt-4o"],
    )

    limite_usd = st.number_input(
        "Limite de custo por projeto (US$)",
        min_value=0.10,
        max_value=1000.0,
        value=5.0,
        step=0.50,
    )

    max_tokens = st.slider(
        "Tokens máximos por capítulo",
        min_value=1000,
        max_value=8000,
        value=5000,
        step=500,
    )

    st.caption(
        "A API é cobrada separadamente. Os preços no código são "
        "referências e devem ser conferidos antes do uso."
    )


# ==========================================================
# INTERFACE
# ==========================================================

st.title("📚 Atlas Studio")
st.subheader("Editora & Publicador")

st.write(
    "Gere seu manuscrito por etapas, acompanhe os custos, "
    "salve o progresso e exporte o miolo em PDF."
)

aba_novo, aba_salvos, aba_revisao = st.tabs([
    "Projeto editorial",
    "Projetos salvos",
    "Revisar manuscrito",
])


# ==========================================================
# PROJETOS SALVOS
# ==========================================================

with aba_salvos:
    arquivos = sorted(
        PASTA_PROJETOS.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not arquivos:
        st.info("Ainda não existem projetos salvos.")
    else:
        opcoes = {
            f"{p.stem} — {datetime.fromtimestamp(p.stat().st_mtime):%d/%m/%Y %H:%M}": str(p)
            for p in arquivos
        }

        selecionado = st.selectbox(
            "Escolha um projeto",
            list(opcoes.keys()),
        )

        if st.button("Carregar projeto"):
            st.session_state["projeto_atlas"] = carregar_projeto(
                opcoes[selecionado]
            )
            st.success("Projeto carregado. Abra a aba Projeto editorial.")
            st.rerun()

        st.caption(
            "Os projetos são salvos na pasta atlas_projects. "
            "Faça cópias de segurança dessa pasta."
        )


# ==========================================================
# CRIAÇÃO E RETOMADA
# ==========================================================

with aba_novo:
    projeto_atual = st.session_state.get("projeto_atlas")

    if projeto_atual:
        st.info(
            f"Projeto em andamento: {projeto_atual['titulo']} — "
            f"{len(projeto_atual.get('capitulos', []))} capítulo(s) salvo(s)."
        )

    with st.form("form_projeto"):
        titulo = st.text_input(
            "Título do livro",
            value=(projeto_atual or {}).get("titulo", ""),
        )

        autor = st.text_input(
            "Nome do autor",
            value=(projeto_atual or {}).get("autor", ""),
        )

        genero = st.selectbox(
            "Gênero literário",
            [
                "Romance literário",
                "Mistério / suspense",
                "Fantasia épica",
                "Ficção histórica",
                "Desenvolvimento pessoal / filosofia",
            ],
        )

        premissa = st.text_area(
            "Premissa ou sinopse",
            value=(projeto_atual or {}).get("premissa", ""),
            height=120,
        )

        tom = st.selectbox(
            "Tom de voz",
            [
                "Clássico, atmosférico e misterioso",
                "Contemplativo, poético e reflexivo",
                "Dramático e envolvente",
                "Direto e acessível",
            ],
        )

        quantidade = st.slider(
            "Número de capítulos",
            4, 20,
            int((projeto_atual or {}).get("quantidade", 12)),
        )

        paginas_minimas = st.number_input(
            "Páginas mínimas por capítulo",
            min_value=11,
            max_value=30,
            value=int((projeto_atual or {}).get("paginas_minimas", 11)),
        )

        palavras_por_pagina = st.slider(
            "Estimativa de palavras por página",
            min_value=180,
            max_value=350,
            value=int((projeto_atual or {}).get("palavras_por_pagina", 250)),
            step=10,
        )

        biografia = st.text_area(
            "Biografia do autor",
            value=(projeto_atual or {}).get("biografia", ""),
        )

        salvar_dados = st.form_submit_button(
            "Salvar dados do projeto",
            type="primary",
        )

    if salvar_dados:
        if projeto_atual:
            projeto = projeto_atual
        else:
            projeto = {
                "capitulos": [],
                "estrutura": [],
                "revisoes": {},
                "uso": {
                    "entrada": 0,
                    "saida": 0,
                    "custo_usd": 0.0,
                },
            }

        projeto.update({
            "titulo": titulo.strip(),
            "autor": autor.strip(),
            "genero": genero,
            "premissa": premissa.strip(),
            "tom": tom,
            "quantidade": quantidade,
            "paginas_minimas": int(paginas_minimas),
            "palavras_por_pagina": int(palavras_por_pagina),
            "meta_palavras": int(paginas_minimas * palavras_por_pagina),
            "biografia": biografia.strip(),
            "modelo": modelo,
            "limite_usd": float(limite_usd),
        })

        st.session_state["projeto_atlas"] = projeto
        destino = salvar_projeto(projeto)
        st.success(f"Projeto salvo: {destino}")

    projeto = st.session_state.get("projeto_atlas")

    if projeto:
        meta = projeto.get(
            "meta_palavras",
            projeto.get("paginas_minimas", 11)
            * projeto.get("palavras_por_pagina", 250),
        )

        st.markdown("### Meta editorial")
        st.write(
            f"Meta aproximada: **{meta:,} palavras por capítulo** "
            f"para tentar alcançar {projeto['paginas_minimas']} páginas."
            .replace(",", ".")
        )

        concluidos = len(projeto.get("capitulos", []))
        total = projeto["quantidade"]

        st.progress(min(concluidos / total, 1.0))
        st.write(f"Capítulos concluídos: **{concluidos}/{total}**")

        uso = projeto.get("uso", {})
        custo = uso.get("custo_usd", 0.0)
        limite_atual = projeto.get("limite_usd", limite_usd)

        st.write(
            f"Tokens de entrada: {uso.get('entrada', 0):,} · "
            f"tokens de saída: {uso.get('saida', 0):,}"
            .replace(",", ".")
        )
        st.write(f"**Custo estimado acumulado: US$ {custo:.4f}**")

        if custo >= limite_atual:
            st.error(
                "Limite de orçamento atingido. A geração está bloqueada "
                "até você aumentar o limite conscientemente."
            )
        elif limite_atual > 0:
            st.caption(
                f"Saldo estimado: US$ {limite_atual - custo:.4f}"
            )

        if st.button("Gerar / retomar manuscrito", type="primary"):
            if not api_key.strip():
                st.error("Informe a chave da API na barra lateral.")
            elif not projeto.get("titulo") or not projeto.get("premissa"):
                st.error("Preencha título e premissa e salve os dados.")
            elif projeto.get("uso", {}).get("custo_usd", 0) >= projeto.get(
                "limite_usd", limite_usd
            ):
                st.error("O limite de orçamento foi atingido.")
            else:
                cliente = OpenAI(api_key=api_key.strip())

                try:
                    # A estrutura só é criada se ainda não existir.
                    if not projeto.get("estrutura"):
                        prompt_estrutura = f"""
Crie exatamente {projeto['quantidade']} títulos de capítulos para o livro
"{projeto['titulo']}".

Gênero: {projeto['genero']}
Premissa: {projeto['premissa']}
Tom: {projeto['tom']}

Crie progressão lógica, variedade narrativa e um desfecho coerente.
Responda somente com uma lista numerada, um título por linha.
"""
                        texto, uso_chamada = chamada_ia(
                            cliente,
                            modelo,
                            [
                                {
                                    "role": "system",
                                    "content": "Você é um editor literário experiente. Escreva em português brasileiro.",
                                },
                                {
                                    "role": "user",
                                    "content": prompt_estrutura,
                                },
                            ],
                            max_tokens=1500,
                        )

                        registrar_uso(projeto, uso_chamada, modelo)
                        salvar_projeto(projeto)

                        if projeto["uso"]["custo_usd"] >= projeto["limite_usd"]:
                            st.error(
                                "Limite atingido durante o planejamento. "
                                "A estrutura foi salva; a geração foi interrompida."
                            )
                            st.stop()

                        titulos = extrair_titulos(
                            texto,
                            projeto["quantidade"],
                        )

                        if len(titulos) != projeto["quantidade"]:
                            salvar_projeto(projeto)
                            st.error(
                                f"A IA retornou {len(titulos)} títulos, "
                                f"mas eram esperados {projeto['quantidade']}. "
                                "Tente novamente."
                            )
                            st.stop()

                        projeto["estrutura"] = titulos
                        salvar_projeto(projeto)

                    concluidos_por_numero = {
                        c["numero"]: c
                        for c in projeto.get("capitulos", [])
                    }

                    barra = st.progress(0)
                    status = st.empty()

                    for numero, titulo_capitulo in enumerate(
                        projeto["estrutura"], start=1
                    ):
                        # Não cobra novamente pelos capítulos já salvos.
                        if numero in concluidos_por_numero:
                            barra.progress(numero / total)
                            continue

                        custo_atual = projeto["uso"]["custo_usd"]

                        if custo_atual >= projeto["limite_usd"]:
                            salvar_projeto(projeto)
                            status.error(
                                "Orçamento atingido. Progresso salvo."
                            )
                            break

                        status.write(
                            f"Escrevendo capítulo {numero}/{total}: "
                            f"{titulo_capitulo}"
                        )

                        anteriores = projeto.get("capitulos", [])[-6:]

                        memoria = "\n".join(
                            f"Capítulo {c['numero']} — {c['titulo']}: "
                            f"{c.get('resumo', '')}"
                            for c in anteriores
                        ) or "Nenhum capítulo anterior."

                        prompt_capitulo = f"""
Escreva o capítulo {numero} de {total} do livro "{projeto['titulo']}".

Autor: {projeto['autor']}
Gênero: {projeto['genero']}
Premissa: {projeto['premissa']}
Tom: {projeto['tom']}
Título do capítulo: {titulo_capitulo}

Meta: aproximadamente {projeto['meta_palavras']} palavras.
A meta busca atingir pelo menos {projeto['paginas_minimas']} páginas
em um livro de 14 x 21 cm, mas a paginação será conferida depois.

Desenvolva cenas, personagens, conflitos, diálogos e consequências.
Não repita ideias apenas para aumentar o volume.
Mantenha nomes, motivações, cronologia e ambientação consistentes.

Resumo dos capítulos anteriores:
{memoria}

Escreva em português brasileiro natural.
Não inclua notas editoriais, comentários sobre o processo ou instruções.
Entregue somente o texto do capítulo.
"""

                        texto_capitulo, uso_capitulo = chamada_ia(
                            cliente,
                            modelo,
                            [
                                {
                                    "role": "system",
                                    "content": "Você é um romancista profissional. Priorize qualidade literária, continuidade e português brasileiro.",
                                },
                                {
                                    "role": "user",
                                    "content": prompt_capitulo,
                                },
                            ],
                            temperatura=0.75,
                            max_tokens=max_tokens,
                        )

                        registrar_uso(projeto, uso_capitulo, modelo)

                        if not texto_capitulo:
                            salvar_projeto(projeto)
                            raise RuntimeError(
                                f"O capítulo {numero} voltou vazio."
                            )

                        # Gera um resumo curto para manter a continuidade.
                        resumo, uso_resumo = chamada_ia(
                            cliente,
                            modelo,
                            [{
                                "role": "user",
                                "content": (
                                    "Resuma em até 120 palavras os acontecimentos, "
                                    "personagens, revelações e ganchos deste capítulo. "
                                    "Não invente fatos.\n\n" + texto_capitulo
                                ),
                            }],
                            temperatura=0.2,
                            max_tokens=250,
                        )

                        registrar_uso(projeto, uso_resumo, modelo)

                        projeto.setdefault("capitulos", []).append({
                            "numero": numero,
                            "titulo": titulo_capitulo,
                            "texto": texto_capitulo,
                            "resumo": resumo,
                            "palavras": contar_palavras(texto_capitulo),
                            "criado_em": datetime.now().isoformat(
                                timespec="seconds"
                            ),
                        })

                        # Ponto de salvamento após cada capítulo completo.
                        salvar_projeto(projeto)
                        barra.progress(numero / total)

                        status.write(
                            f"Capítulo {numero} salvo — "
                            f"{contar_palavras(texto_capitulo):,} palavras."
                            .replace(",", ".")
                        )

                        if projeto["uso"]["custo_usd"] >= projeto["limite_usd"]:
                            status.warning(
                                "Limite atingido após salvar o capítulo. "
                                "Aumente o orçamento para continuar."
                            )
                            break

                    st.session_state["projeto_atlas"] = projeto
                    salvar_projeto(projeto)
                    st.success(
                        "Progresso salvo. Você pode retomar a geração "
                        "a qualquer momento."
                    )
                    st.rerun()

                except Exception as erro:
                    salvar_projeto(projeto)
                    st.session_state["projeto_atlas"] = projeto
                    st.error(f"Erro durante a geração: {erro}")
                    st.warning(
                        "Os capítulos já concluídos foram salvos. "
                        "Corrija o problema e tente retomar."
                    )

        st.divider()
        st.subheader("Exportação do manuscrito")

        if st.button("Gerar PDF 14 × 21 cm"):
            capitulos = sorted(
                projeto.get("capitulos", []),
                key=lambda c: c["numero"],
            )

            if not capitulos:
                st.error("Gere pelo menos um capítulo primeiro.")
            else:
                try:
                    pdf = criar_pdf(
                        projeto["titulo"],
                        projeto["autor"],
                        [
                            {"titulo": c["titulo"], "texto": c["texto"]}
                            for c in capitulos
                        ],
                        projeto.get("biografia", ""),
                    )

                    total_paginas, relatorio = conferir_pdf(pdf, [
                        {"titulo": c["titulo"], "texto": c["texto"]}
                        for c in capitulos
                    ])

                    st.session_state["atlas_pdf"] = pdf
                    st.session_state["atlas_pdf_nome"] = (
                        nome_seguro(projeto["titulo"]) + "_miolo.pdf"
                    )
                    st.session_state["atlas_pdf_paginas"] = total_paginas
                    st.session_state["atlas_pdf_relatorio"] = relatorio

                except Exception as erro:
                    st.error(f"Erro ao gerar ou conferir o PDF: {erro}")

        if st.session_state.get("atlas_pdf"):
            st.download_button(
                "📥 Baixar miolo em PDF",
                data=st.session_state["atlas_pdf"],
                file_name=st.session_state["atlas_pdf_nome"],
                mime="application/pdf",
                type="primary",
            )

            st.write(
                f"Total de páginas no arquivo: "
                f"**{st.session_state['atlas_pdf_paginas']}**"
            )

            st.subheader("Relatório aproximado de páginas")

            for item in st.session_state["atlas_pdf_relatorio"]:
                if item["paginas"] < projeto["paginas_minimas"]:
                    st.warning(
                        f"Capítulo {item['numero']} — {item['titulo']}: "
                        f"{item['paginas']} página(s). Meta: "
                        f"{projeto['paginas_minimas']}."
                    )
                else:
                    st.success(
                        f"Capítulo {item['numero']} — {item['titulo']}: "
                        f"{item['paginas']} páginas."
                    )

            st.caption(
                "A extração automática do PDF pode falhar em alguns layouts. "
                "Confira visualmente as quebras e o início e fim de cada capítulo."
            )

        if projeto.get("capitulos"):
            st.subheader("Capítulos concluídos")

            for capitulo in sorted(
                projeto["capitulos"],
                key=lambda c: c["numero"],
            ):
                with st.expander(
                    f"Capítulo {capitulo['numero']} — "
                    f"{capitulo['titulo']} · "
                    f"{capitulo.get('palavras', contar_palavras(capitulo['texto']))} palavras"
                ):
                    st.text_area(
                        "Texto do capítulo",
                        value=capitulo["texto"],
                        height=260,
                        disabled=True,
                        key=f"texto_capitulo_{capitulo['numero']}",
                    )


# ==========================================================
# REVISÃO COM PRESERVAÇÃO DO ORIGINAL
# ==========================================================

with aba_revisao:
    projeto = st.session_state.get("projeto_atlas")

    if not projeto or not projeto.get("capitulos"):
        st.info(
            "Carregue ou gere um projeto com capítulos para habilitar a revisão."
        )
    else:
        st.write(
            "A versão revisada ficará separada do original. "
            "Você decide se quer aprová-la."
        )

        opcoes_capitulos = {
            f"Capítulo {c['numero']} — {c['titulo']}": c["numero"]
            for c in sorted(
                projeto["capitulos"],
                key=lambda c: c["numero"],
            )
        }

        escolhido = st.selectbox(
            "Capítulo para revisar",
            list(opcoes_capitulos.keys()),
        )

        numero_escolhido = opcoes_capitulos[escolhido]
        capitulo = next(
            c for c in projeto["capitulos"]
            if c["numero"] == numero_escolhido
        )

        instrucao = st.text_area(
            "Orientações da revisão",
            "Melhore clareza, gramática, fluidez e ritmo sem alterar os acontecimentos, os personagens ou o sentido do texto.",
        )

        if st.button("Gerar versão revisada"):
            if not api_key.strip():
                st.error("Informe a chave da API na barra lateral.")
            elif projeto["uso"]["custo_usd"] >= projeto["limite_usd"]:
                st.error("Limite de orçamento atingido.")
            else:
                try:
                    cliente = OpenAI(api_key=api_key.strip())

                    revisado, uso = chamada_ia(
                        cliente,
                        modelo,
                        [
                            {
                                "role": "system",
                                "content": (
                                    "Você é um editor literário. Preserve os fatos, "
                                    "a intenção e a personalidade dos personagens. "
                                    "Não invente acontecimentos."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Instruções: {instrucao}\n"
                                    f"Título: {capitulo['titulo']}\n"
                                    "Revise o texto e entregue somente a versão final:\n\n"
                                    + capitulo["texto"]
                                ),
                            },
                        ],
                        temperatura=0.25,
                        max_tokens=max_tokens,
                    )

                    registrar_uso(projeto, uso, modelo)

                    projeto.setdefault("revisoes", {})[
                        str(numero_escolhido)
                    ] = {
                        "texto": revisado,
                        "instrucoes": instrucao,
                        "criada_em": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    }

                    salvar_projeto(projeto)
                    st.session_state["projeto_atlas"] = projeto
                    st.success(
                        "Revisão salva separadamente. O original continua intacto."
                    )
                    st.rerun()

                except Exception as erro:
                    salvar_projeto(projeto)
                    st.error(f"Falha na revisão: {erro}")

        revisao = projeto.get("revisoes", {}).get(
            str(numero_escolhido)
        )

        if revisao:
            coluna_original, coluna_revisada = st.columns(2)

            with coluna_original:
                st.markdown("**Texto original**")
                st.text_area(
                    "Original",
                    capitulo["texto"],
                    height=350,
                    disabled=True,
                    key=f"original_{numero_escolhido}",
                )

            with coluna_revisada:
                st.markdown("**Texto revisado**")
                st.text_area(
                    "Revisado",
                    revisao["texto"],
                    height=350,
                    disabled=True,
                    key=f"revisado_{numero_escolhido}",
                )

            if st.button("Aprovar e substituir o original"):
                capitulo["texto"] = revisao["texto"]
                capitulo["palavras"] = contar_palavras(revisao["texto"])

                projeto["revisoes"].pop(str(numero_escolhido), None)
                salvar_projeto(projeto)
                st.session_state["projeto_atlas"] = projeto
                st.success("Revisão aprovada e projeto salvo.")
                st.rerun()

            if st.button("Descartar versão revisada"):
                projeto["revisoes"].pop(str(numero_escolhido), None)
                salvar_projeto(projeto)
                st.session_state["projeto_atlas"] = projeto
                st.success("Revisão descartada. O original foi preservado.")
                st.rerun()


st.divider()
st.caption(
    "A meta de 11 páginas é verificada depois da diagramação, mas não é "
    "garantida pela contagem de palavras. O relatório automático é aproximado. "
    "Faça backup da pasta atlas_projects e confira o PDF antes de publicar."
)
