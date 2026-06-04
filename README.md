# 🎙️ Voice RAG Support

> Assistente de suporte técnico ativado por voz com busca semântica em tempo real.

## 🌐 Visão Geral

O **Voice RAG Support** é um assistente de suporte técnico que combina reconhecimento de voz em tempo real com busca semântica em documentação técnica. O usuário fala sua dúvida pelo microfone — o sistema transcreve, busca a solução mais relevante na base de conhecimento e retorna uma resposta concisa otimizada para voz.

### Principais características

- **Voz em tempo real** — transcrição contínua com o Azure Speech SDK sem latência perceptível
- **RAG (Retrieval-Augmented Generation)** — respostas embasadas em documentação técnica real
- **Streaming de tokens** — a resposta aparece palavra por palavra enquanto é gerada
- **Memória conversacional** — o assistente lembra do contexto da conversa atual
- **Fallback por texto** — funciona também via digitação quando microfone não está disponível
- **100% assíncrono** — backend FastAPI com `asyncio` para suporte a múltiplas sessões simultâneas

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Streamlit)                      │
│  Captura de microfone · WebRTC · Exibição de tokens         │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket (chunks de áudio / tokens)
┌────────────────────────▼────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  Orquestração assíncrona · ConnectionManager · Roteamento   │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼────────────────┐
│  Azure Cognitive    │      │     LangChain (RAG)          │
│  Services (STT)     │─────▶│  Chain · Memória · Prompt   │
│  Transcrição em     │      └────────────┬────────────────┘
│  tempo real         │                   │
└─────────────────────┘      ┌────────────▼────────────────┐
                             │   ChromaDB + BAAI/bge-m3     │
                             │   Embeddings · Busca MMR     │
                             └─────────────────────────────┘
```

---

## ✅ Pré-requisitos

| Requisito | Versão mínima | Observação |
|---|---|---|
| Python | 3.13+ | Obrigatório — `audioop` removido em 3.13, já tratado |
| pip | 23+ | `pip install --upgrade pip` |
| Conta Azure | — | Tier gratuito F0 disponível |
| Conta OpenRouter | — | Plano gratuito disponível |
| Conta HuggingFace | — | Gratuito — token opcional mas recomendado |

---

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/voice-rag-support.git
cd voice-rag-support
```

### 2. Crie e ative o ambiente virtual

```bash
# Criar o venv
python -m venv .venv

# Ativar — Linux/macOS
source .venv/bin/activate

# Ativar — Windows PowerShell
.venv\Scripts\Activate.ps1

# Ativar — Windows CMD
.venv\Scripts\activate.bat
```

### 3. Atualize o pip

```bash
pip install --upgrade pip setuptools wheel
```

### 4. Instale as dependências

```bash
# Backend — FastAPI + WebSocket
pip install fastapi "uvicorn[standard]" websockets python-dotenv pydantic pydantic-settings

# Azure Speech SDK
pip install azure-cognitiveservices-speech

# IA & Orquestração — LangChain + OpenRouter
pip install langchain langchain-openai langchain-community langchain-huggingface langchain-text-splitters

# Vector Store
pip install chromadb

# Embeddings e processamento de áudio
pip install sentence-transformers numpy scipy

# Ingestão de documentos
pip install pypdf unstructured markdown

# Frontend
pip install streamlit streamlit-webrtc av
```

### 5. Gere o requirements.txt

```bash
pip freeze > requirements.txt
```

---

## ⚙️ Configuração

### 1. Copie o template de variáveis de ambiente

```bash
cp .env.example .env
```

### 2. Preencha o `.env`

```bash
# Azure Speech-to-Text
AZURE_SPEECH_KEY=sua_key_aqui
AZURE_SPEECH_REGION=brazilsouth

# OpenRouter (LLM)
OPENROUTER_API_KEY=sk-or-v1-sua_key_aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-4-31b-it:free

# Embeddings — modelo local, sem chave
EMBEDDING_MODEL=BAAI/bge-m3

# HuggingFace (opcional — aumenta rate limit de download)
HF_TOKEN=hf_sua_token_aqui
HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Vector Store
CHROMA_PERSIST_DIR=./knowledge_base/vector_store

# App
LOG_LEVEL=INFO
```

### Como obter as credenciais

<details>
<summary><strong>Azure Speech — Key + Region</strong></summary>

1. Acesse [portal.azure.com](https://portal.azure.com) e faça login
2. Pesquise por **Speech Services** na barra de busca
3. Clique em **Criar** e selecione o pricing tier **Free F0**
4. Escolha a região **Brazil South** para menor latência
5. Após criar, vá em **Keys and Endpoint** no menu lateral
6. Copie **KEY 1** → `AZURE_SPEECH_KEY`
7. Copie **Location/Region** (ex: `brazilsouth`) → `AZURE_SPEECH_REGION`

> O tier Free F0 inclui 5 horas de áudio por mês — suficiente para desenvolvimento.
</details>

<details>
<summary><strong>OpenRouter — API Key</strong></summary>

1. Acesse [openrouter.ai](https://openrouter.ai) e crie sua conta
2. No menu lateral, clique em **Keys**
3. Clique em **Create Key** e dê um nome (ex: `voice-rag`)
4. Copie a chave gerada — começa com `sk-or-v1-`
5. Cole como `OPENROUTER_API_KEY` no `.env`

> O modelo `google/gemma-4-31b-it:free` não exige créditos para desenvolvimento.
</details>

<details>
<summary><strong>HuggingFace Token (opcional)</strong></summary>

1. Acesse [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Clique em **Create new Access Token**
3. Selecione o tipo **Read**
4. Dê um nome (ex: `Voice-RAG`) e clique em **Create token**
5. Cole como `HF_TOKEN` no `.env`

> Sem o token, o download do modelo funciona mas com rate limit menor.
</details>

---

## 📚 Base de Conhecimento

### 1. Adicione seus documentos

Coloque arquivos PDF e Markdown na pasta `knowledge_base/raw/`:

```
knowledge_base/raw/
├── fastapi_tutorial.pdf
├── langchain_overview.pdf
└── faq_suporte_tecnico.md
```

Formatos suportados: `.pdf`, `.md`, `.txt`

### 2. Execute o pipeline de ingestão

```bash
python scripts/ingest_docs.py
```

O script executa automaticamente:
- **Loader** — lê todos os arquivos da pasta `raw/`
- **Splitter** — divide em chunks de 512 caracteres com overlap de 50
- **Embeddings** — gera vetores com BAAI/bge-m3 (~570 MB, download automático)
- **ChromaDB** — persiste os vetores em `knowledge_base/vector_store/`

> Na primeira execução o modelo BAAI/bge-m3 (~2.27 GB) será baixado automaticamente. As execuções seguintes usam o cache local.

### 3. Atualizando a base

Para adicionar novos documentos sem reprocessar tudo:

```python
from backend.ingest.embeddings import update_vectorstore
from backend.ingest.loader import load_documents
from backend.ingest.splitter import split_documents

docs = load_documents("knowledge_base/raw/novo_arquivo.pdf")
chunks = split_documents(docs)
update_vectorstore(chunks)
```

---

## ▶️ Execução

### Verificar saúde do sistema antes de iniciar

```bash
python -c "import fastapi; print('FastAPI OK')"
python -c "import langchain; print('LangChain OK')"
python -c "import chromadb; print('ChromaDB OK')"
python -c "import azure.cognitiveservices.speech; print('Azure Speech OK')"
python -c "import streamlit; print('Streamlit OK')"
```

### Terminal 1 — Backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verifique o health check:

```bash
curl http://localhost:8000/health
# Esperado: {"status": "ok", "rag_ready": true}
```

### Terminal 2 — Frontend

```bash
cd frontend
streamlit run app.py
```

Acesse [http://localhost:8501](http://localhost:8501) no navegador.

### Como usar

1. Clique no botão **Start** no componente de captura de voz
2. Permita o acesso ao microfone quando o navegador solicitar
3. Fale sua dúvida técnica
4. Acompanhe a transcrição em tempo real e a resposta sendo gerada token por token
5. Use o campo de texto como alternativa ao microfone

---

## 📁 Estrutura do Projeto

```
voice-rag-support/
│
├── backend/                        # FastAPI — núcleo assíncrono
│   ├── main.py                     # App FastAPI, rotas e WebSocket handler
│   ├── config.py                   # Variáveis de ambiente (pydantic-settings)
│   │
│   ├── speech/
│   │   ├── azure_stt.py            # Integração Azure Speech SDK (stream contínuo)
│   │   └── audio_utils.py          # Conversão de formato de áudio (numpy/scipy)
│   │
│   ├── rag/
│   │   ├── chain.py                # Pipeline RAG com memória conversacional
│   │   ├── retriever.py            # ChromaDB + busca MMR
│   │   └── prompts.py              # System prompt + templates LangChain
│   │
│   └── ingest/
│       ├── loader.py               # Leitura de PDFs e Markdowns
│       ├── splitter.py             # Chunking com RecursiveCharacterTextSplitter
│       └── embeddings.py           # Geração e persistência de embeddings
│
├── frontend/                       # Streamlit — interface de usuário
│   ├── app.py                      # Página principal e gerenciamento de estado
│   └── audio_recorder.py           # Captura WebRTC + comunicação WebSocket
│
├── knowledge_base/                 # Base de conhecimento
│   ├── raw/                        # Arquivos PDF e Markdown originais
│   └── vector_store/               # Índice ChromaDB persistido (gerado)
│
├── scripts/
│   └── ingest_docs.py              # Script de ingestão da base de conhecimento
│
├── tests/
│   ├── test_stt.py
│   ├── test_chain.py
│   └── test_websocket.py
│
├── .env                            # Variáveis de ambiente reais (nunca commitar)
├── .env.example                    # Template de variáveis (commitar)
├── .gitignore
├── docker-compose.yml
└── requirements.txt
```

---

## 🔄 Fluxo de Dados

```
Usuário fala
    │
    ▼
Streamlit (WebRTC)
    │ captura frames de áudio
    ▼
audio_recorder.py
    │ converte para PCM 16kHz mono (numpy/scipy)
    │ divide em chunks de 100ms
    ▼
WebSocket → FastAPI
    │
    ├──▶ receive_loop()          ← recebe chunks continuamente
    │         │
    │         ▼ asyncio.Queue
    │
    └──▶ stt_and_rag_loop()     ← processa em paralelo
              │
              ▼
         Azure STT (stream contínuo)
              │ transcrição
              ▼
         LangChain RAG Chain
              │
              ├── CONDENSE_QUESTION_PROMPT  ← reformula com histórico
              ├── ChromaDB MMR Retriever    ← busca 4 chunks relevantes
              ├── RAG_PROMPT                ← monta contexto + pergunta
              └── OpenRouter (Gemma 4)      ← gera resposta
                       │
                       ▼ astream (token por token)
              WebSocket → Streamlit
                       │
                       ▼
              Exibição em tempo real
```

---

## 🛠️ Tecnologias

| Camada | Tecnologia | Versão | Função |
|---|---|---|---|
| Frontend | Streamlit | 1.35+ | Interface de usuário |
| Frontend | streamlit-webrtc | 0.47+ | Captura de microfone |
| Backend | FastAPI | 0.111+ | API assíncrona + WebSocket |
| Backend | Uvicorn | 0.29+ | ASGI server |
| STT | Azure Cognitive Services | 1.37+ | Speech-to-Text em stream |
| Orquestração | LangChain | 0.2+ | RAG + memória + prompts |
| LLM | OpenRouter / Gemma 4 | — | Geração de respostas |
| Embeddings | BAAI/bge-m3 | — | Vetorização de documentos |
| Vector Store | ChromaDB | 0.5+ | Armazenamento e busca semântica |
| Áudio | NumPy + SciPy | — | Conversão e processamento de áudio |

---

## 👤 Autor

Desenvolvido como projeto de assistente de suporte técnico por voz com arquitetura RAG.

---

<p align="center">
  Feito com FastAPI · LangChain · Azure Speech · Streamlit
</p>