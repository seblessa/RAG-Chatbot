# Projeto RAG (Retrieval-Augmented Generation)

Este projeto implementa um sistema de RAG utilizando Qdrant, OpenSearch e LLMSherpa para indexação e recuperação de documentos. O sistema permite fazer perguntas a partir de documentos carregados.

## Requisitos

- **Python** 3.12.0
- **Docker Desktop** (para executar Qdrant, OpenSearch e LLMSherpa)

## Setup do Ambiente

1. **Instalar os requisitos:**
   - Crie um ambiente virtual e ative-o:
     ```bash
     python -m venv venv
     source venv/bin/activate  # Para Linux/Mac
     .\venv\Scripts\activate  # Para Windows
     ```
   - Instale as dependências necessárias:
     ```bash
     pip install -r requirements.txt
     ```

2. **Instalar e configurar o Docker Desktop.**

3. **Executar os serviços necessários:**

   - **Qdrant:**
     ```bash
     docker pull qdrant/qdrant
     docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
     ```

   - **LLMSherpa:**
     ```bash
     docker pull ghcr.io/nlmatics/nlm-ingestor:latest
     docker run -d -p 5010:5001 ghcr.io/nlmatics/nlm-ingestor:latest
     ```

   - **OpenSearch:**
     ```bash
     docker pull opensearchproject/opensearch:2
     docker run -d -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Master_pw_123!#" opensearchproject/opensearch:latest
     ```

4. **Executar o arquivo `app.py`:**
   ```bash
   python app.py

5. **Interação com a interface**

    Na interface do aplicativo, escolha a opção **Upload**.  
    Selecione o ficheiro **"CELEX"**.  
    Aguarde até que apareça uma janela indicando que a operação foi concluída com sucesso.

6. **Fazer perguntas**

    Após o upload, você pode fazer perguntas e aguardar as respostas.

7. **Gestão de Documentos**

    Para eliminar ou inserir novos documentos:

    A forma mais fácil é eliminar os containers do Qdrant e OpenSearch e criá-los novamente. Você pode fazer isso com os seguintes comandos:

    ```bash
    docker rm -f <container_id>
