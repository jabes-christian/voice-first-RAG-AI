# FAQ Técnico — Assistente de Suporte por Voz (Voice RAG Support)

## Visão Geral do Sistema

### O que é o Voice RAG Support?
O Voice RAG Support é um assistente de suporte técnico ativado por voz. O usuário fala sua dúvida pelo microfone, o sistema transcreve o áudio em tempo real usando o Azure Speech-to-Text, busca a solução mais relevante na base de conhecimento técnica e retorna uma resposta concisa e direta, otimizada para ser ouvida (não lida).

### Quais tecnologias compõem o sistema?
O sistema é composto por cinco camadas principais:
- **Frontend**: Streamlit com captura de áudio via WebRTC
- **Backend**: FastAPI com comunicação assíncrona via WebSocket
- **Speech-to-Text**: Azure Cognitive Services Speech SDK em modo contínuo
- **Orquestração de IA**: LangChain com RAG (Retrieval-Augmented Generation)
- **Base de conhecimento**: ChromaDB com embeddings BAAI/bge-m3

---

## Instalação e Configuração

### Como configurar o ambiente pela primeira vez?
Execute os seguintes passos em ordem:

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 2. Atualizar pip
pip install --upgrade pip setuptools wheel

# 3. Instalar todas as dependências
pip install fastapi "uvicorn[standard]" websockets python-dotenv pydantic
pip install azure-cognitiveservices-speech
pip install langchain langchain-openai langchain-community langchain-huggingface
pip install chromadb sentence-transformers
pip install pypdf unstructured markdown langchain-text-splitters
pip install numpy scipy
pip install streamlit streamlit-webrtc av
pip install pydantic-settings
```

### Quais variáveis de ambiente são obrigatórias?
Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```
AZURE_SPEECH_KEY=sua_chave_aqui
AZURE_SPEECH_REGION=brazilsouth
OPENROUTER_API_KEY=sk-or-v1-sua_chave_aqui
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-4-31b-it:free
EMBEDDING_MODEL=BAAI/bge-m3
CHROMA_PERSIST_DIR=./knowledge_base/vector_store
LOG_LEVEL=INFO
```

### Como obter a chave do Azure Speech?
1. Acesse portal.azure.com e faça login
2. Pesquise por "Speech Services" na barra de busca
3. Clique em "Criar" e escolha o pricing tier "Free F0"
4. Selecione a região "Brazil South" para menor latência
5. Após criar, acesse o recurso e vá em "Keys and Endpoint"
6. Copie a "KEY 1" — esse é o valor para `AZURE_SPEECH_KEY`
7. Copie a "Location/Region" — esse é o valor para `AZURE_SPEECH_REGION`

### Como obter a chave do OpenRouter?
1. Acesse openrouter.ai e crie uma conta gratuita
2. No menu lateral, clique em "Keys"
3. Clique em "Create Key" e dê um nome descritivo (ex: voice-rag)
4. Copie a chave gerada — ela começa com `sk-or-v1-`
5. Cole no `.env` como `OPENROUTER_API_KEY`

O modelo `google/gemma-4-31b-it:free` não exige créditos para uso em desenvolvimento.

---

## Base de Conhecimento

### Como popular a base de conhecimento?
Coloque seus arquivos PDF e Markdown na pasta `knowledge_base/raw/` e execute:

```bash
python scripts/ingest_docs.py
```

O script vai carregar os arquivos, dividi-los em chunks de 512 caracteres, gerar os embeddings com o modelo BAAI/bge-m3 e persistir tudo no ChromaDB.

### Quais formatos de arquivo são suportados?
O sistema suporta três formatos:
- `.pdf` — documentos PDF (extraídos página a página)
- `.md` — arquivos Markdown
- `.txt` — arquivos de texto puro

### Como atualizar a base sem reprocessar tudo?
Use a função `update_vectorstore` do `embeddings.py` para adicionar apenas os novos documentos sem reprocessar os já existentes. Isso é útil quando você adiciona um novo manual ou atualiza um FAQ específico.

### Por que usar o modelo BAAI/bge-m3 para embeddings?
O BAAI/bge-m3 é um modelo multilíngue de alta qualidade que:
- Suporta português nativamente com boa performance
- Tem context window de 8192 tokens — adequado para chunks maiores
- Roda localmente sem custo de API
- É baixado automaticamente na primeira execução (~570 MB em cache)

### O que é chunk_size e chunk_overlap?
- `chunk_size=512`: cada pedaço de texto tem no máximo 512 caracteres. Isso equilibra contexto rico com custo de tokens no prompt.
- `chunk_overlap=50`: os últimos 50 caracteres de um chunk são repetidos no início do próximo. Isso evita que uma informação importante seja cortada exatamente na borda entre dois chunks.

---

## Execução do Sistema

### Como iniciar o servidor backend?
Com o ambiente virtual ativado e a base de conhecimento populada, execute:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

O servidor estará disponível em `http://localhost:8000`. Para verificar se está funcionando, acesse `http://localhost:8000/health` — deve retornar `{"status": "ok", "rag_ready": true}`.

### Como iniciar o frontend Streamlit?
Em outro terminal (com o venv ativado):

```bash
streamlit run frontend/app.py
```

O Streamlit abrirá automaticamente no navegador em `http://localhost:8501`.

### Como verificar se o backend está saudável?
Acesse a rota de health check:

```bash
curl http://localhost:8000/health
```

A resposta esperada é:
```json
{"status": "ok", "rag_ready": true}
```

Se `rag_ready` for `false`, o pipeline de ingestão ainda não foi executado. Rode `python scripts/ingest_docs.py` primeiro.

---

## Solução de Problemas

### Erro: "audioop not found" no Python 3.13
O módulo `audioop` foi removido do Python 3.13. O projeto já usa `numpy` e `scipy` como substitutos no `audio_utils.py`. Verifique se as dependências estão instaladas:

```bash
pip install numpy scipy
```

### Erro: "AZURE_SPEECH_KEY not found" ao iniciar
Verifique se o arquivo `.env` existe na raiz do projeto e contém a variável `AZURE_SPEECH_KEY`. O `config.py` usa `pydantic-settings` para validar as variáveis — se alguma obrigatória estiver faltando, o servidor não sobe e exibe qual variável está ausente.

### Erro: "No module named 'azure.cognitiveservices.speech'"
O SDK do Azure não está instalado. Execute:

```bash
pip install azure-cognitiveservices-speech
```

### O reconhecimento de voz está muito lento
Verifique a região configurada no `.env`. Para usuários no Brasil, use `AZURE_SPEECH_REGION=brazilsouth` para minimizar a latência de rede até os servidores do Azure.

### A base de conhecimento está vazia ou os resultados são irrelevantes
Execute novamente o pipeline de ingestão após adicionar ou atualizar os documentos:

```bash
python scripts/ingest_docs.py
```

Se o problema persistir, verifique se os arquivos estão na pasta correta (`knowledge_base/raw/`) e se têm extensão suportada (`.pdf`, `.md` ou `.txt`).

### O modelo de embedding demora muito na primeira execução
O modelo BAAI/bge-m3 (~570 MB) é baixado automaticamente do HuggingFace Hub na primeira execução. Esse download ocorre apenas uma vez — nas execuções seguintes o modelo é carregado do cache local em `~/.cache/huggingface/hub/`.

### Erro de autenticação no OpenRouter
Verifique se a chave começa com `sk-or-v1-` e se está corretamente definida como `OPENROUTER_API_KEY` no `.env`. Chaves do OpenRouter são diferentes das chaves da OpenAI — não são intercambiáveis.

### O WebSocket desconecta durante o uso
Verifique se o servidor FastAPI está rodando na porta 8000 e se não há firewall bloqueando conexões WebSocket. Em desenvolvimento, o `--reload` do uvicorn pode causar reconexões ao salvar arquivos — isso é esperado.

---

## Arquitetura e Decisões Técnicas

### Por que WebSocket em vez de requisições HTTP normais?
HTTP fecha a conexão após cada requisição — inviável para streaming de áudio em tempo real. O WebSocket mantém um canal bidirecional persistente, permitindo que o cliente envie chunks de áudio continuamente enquanto o servidor retorna tokens de resposta à medida que são gerados.

### Por que asyncio.gather com duas tasks paralelas?
O recebimento de áudio e o processamento (STT + RAG) são desacoplados em duas tasks assíncronas via `asyncio.gather`. Sem isso, o servidor esperaria o processamento completo antes de receber o próximo chunk de áudio — introduzindo latência crescente em conversas longas.

### Por que PushAudioInputStream em vez de PullAudioInputStream?
No modo Pull, o Azure SDK controla quando puxar os dados. No modo Push, nossa aplicação controla quando enviar — essencial para streams de WebSocket onde os chunks chegam de forma assíncrona e em ritmo irregular.

### Por que call_soon_threadsafe nos callbacks do Azure?
O Azure SDK dispara seus callbacks em threads C++ internas. O `asyncio.Queue` do Python não é thread-safe — escrever nela diretamente de uma thread C++ causaria race conditions. O `call_soon_threadsafe` agenda a operação de forma segura dentro do event loop Python.

### Por que MMR (Maximal Marginal Relevance) no retriever?
A busca por similaridade pura pode retornar 4 chunks quase idênticos do mesmo parágrafo. O MMR equilibra relevância com diversidade — retorna chunks relevantes mas diferentes entre si, enriquecendo o contexto enviado ao LLM.

### Por que max_tokens=256 no LLM?
Respostas para voz precisam ser curtas e diretas. Mais do que 3-4 frases e o usuário perde o fio da meada. O limite de 256 tokens força o modelo a ser conciso — complementado pelo system prompt que reforça essa restrição.

### Por que temperature=0.3?
Suporte técnico exige precisão, não criatividade. Uma temperatura baixa produz respostas mais determinísticas e confiáveis — o modelo segue mais rigorosamente as informações da base de conhecimento em vez de "improvisar".

---

## Estrutura do Projeto

```
voice-rag-support/
├── backend/
│   ├── main.py              # FastAPI + WebSocket handler
│   ├── config.py            # Variáveis de ambiente (pydantic-settings)
│   ├── speech/
│   │   ├── azure_stt.py     # Integração Azure Speech SDK
│   │   └── audio_utils.py   # Conversão de formato de áudio (numpy)
│   ├── rag/
│   │   ├── chain.py         # Pipeline RAG com memória conversacional
│   │   ├── retriever.py     # ChromaDB + busca MMR
│   │   └── prompts.py       # System prompt + templates LangChain
│   └── ingest/
│       ├── loader.py        # Leitura de PDFs e Markdowns
│       ├── splitter.py      # Chunking com RecursiveCharacterTextSplitter
│       └── embeddings.py    # Geração e persistência de embeddings
├── frontend/
│   └── app.py               # Interface Streamlit com captura de áudio
├── knowledge_base/
│   ├── raw/                 # Documentos PDF e Markdown originais
│   └── vector_store/        # Índice ChromaDB persistido
├── scripts/
│   └── ingest_docs.py       # Script de ingestão da base de conhecimento
├── .env                     # Variáveis de ambiente (nunca commitar)
├── .env.example             # Template de variáveis (commitar)
├── .gitignore
└── requirements.txt
```