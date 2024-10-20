from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever  
from haystack_integrations.components.retrievers.opensearch import OpenSearchBM25Retriever  
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack import Pipeline, Document
# from haystack.components import SentenceTransformersRanker 
from haystack.components.joiners.document_joiner import DocumentJoiner as JoinDocuments
from typing import Dict  
from haystack import component
from documents_pipeline.save_stores import get_Osearch_store, get_qdrant_store
from typing import List
  
# Inicializar o DocumentStore  
# qdrant_store = get_qdrant_store()  
# opensearch_store = get_Osearch_store()  
  
# Inicializar os Retrievers  
# sparse_retriever = OpenSearchBM25Retriever(document_store=opensearch_store)  
# dense_retriever = QdrantEmbeddingRetriever(document_store=qdrant_store)  

def get_QDRANT_docs_from_prompt(prompt, document_store=None, retriever=None):  
    """  
    Função que realiza a pesquisa através da prompt específica para a base de dados vetorial.  
    """  
    if not document_store:  
        document_store = get_qdrant_store()  
    if not retriever:  
        retriever = QdrantEmbeddingRetriever(document_store=document_store)  
      
    query_pipeline = Pipeline()
    query_pipeline.add_component("text_embedder", SentenceTransformersTextEmbedder())
    query_pipeline.add_component("retriever", retriever)
    query_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")

    query = prompt

    result = query_pipeline.run({"text_embedder": {"text": query}})
    return result  
  
def get_Osearch_docs_from_prompt(prompt, document_store=None, retriever=None):  
    """  
    Função que realiza a pesquisa através da prompt específica para a base de dados por keywords.  
    """  
    if not document_store:  
        document_store = get_Osearch_store()  
    if not retriever:  
        retriever = OpenSearchBM25Retriever(document_store=document_store, scale_score=True)
      
    query_pipeline = Pipeline()  
    query_pipeline.add_component(name="retriever", instance=retriever)
    query = " ".join(prompt)
    # print(f"RETRIEVER QUERY: {query}")
    result = query_pipeline.run({"retriever": {"query": query}}) 
    return result  

@component  
class QdrantSearch:  
    """  
    Componente para fazer a pesquisa na base de dados vetorial e guardar os resultados no dicionário prompt_mod.  
    """  
    @component.output_types(documents=List[Document])  
    def run(self, prompt_mod: Dict):  
        """  
        Função que obtém os prompts específicos para esta pesquisa, chama a função para fazer a pesquisa.  
        Concatena todos os resultados com score superior a 0.45 e guarda.  
        Guarda a média dos scores dos resultados concatenados.  
        """  
        keyword_prompts = prompt_mod.get("vector_prompt", [])  
        if not keyword_prompts or not isinstance(keyword_prompts, list):  
            raise ValueError("O dicionário de entrada não contém a chave 'vector_prompt' ou ela não é uma lista.")  
          
        all_documents = []
        doc_scores={}
        for keyword_prompt in keyword_prompts:  
            search_results = get_QDRANT_docs_from_prompt(keyword_prompt)
            # print(search_results)  
            all_documents.extend(search_results["retriever"]['documents'])
            for doc in search_results["retriever"]['documents']:
                if doc.id in doc_scores.keys():
                    if doc.score > doc_scores[doc.id]:
                        doc_scores[doc.id]=doc.score
                else:
                    doc_scores[doc.id]=doc.score
        return {"documents":all_documents,"search_params":keyword_prompts, "original_scores":doc_scores}

@component  
class OpenSearch:  
    """  
    Componente para fazer a pesquisa na base de dados OpenSearch e guardar os resultados no dicionário prompt_mod.  
    """  
    @component.output_types(documents=List[Document])  
    def run(self, prompt_mod: Dict):
        """  
        Função que obtém a prompt específica para esta pesquisa, chama a função para fazer a pesquisa e  
        guarda o resultado e o score.  
        """
        keyword_prompts = prompt_mod.get("keyword_prompt", [])
        if not keyword_prompts or not isinstance(keyword_prompts, list):
            raise ValueError("O dicionário de entrada não contém a chave 'keyword_prompt' ou ela não é uma lista.")

        all_documents = []
        doc_scores={}
        for keyword_prompt in keyword_prompts:
            search_results = get_Osearch_docs_from_prompt(keyword_prompt)
            # print(f"OSEARCH RET: {search_results}")
            all_documents.extend(search_results["retriever"]['documents'])
            for doc in search_results["retriever"]['documents']:
                if doc.id in doc_scores.keys():
                    if doc.score > doc_scores[doc.id]:
                        doc_scores[doc.id]=doc.score
                else:
                    doc_scores[doc.id]=doc.score
        return {"documents":all_documents, "search_params":keyword_prompts, "original_scores":doc_scores}
