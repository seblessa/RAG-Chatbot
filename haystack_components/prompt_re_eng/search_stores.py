

from haystack import component

from typing import Dict

from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder


from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.components.retrievers.opensearch import OpenSearchBM25Retriever,OpenSearchEmbeddingRetriever

from haystack import Pipeline

from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder

from ..documents_pipeline.save_stores import get_Osearch_store,get_qdrant_store


def get_QDRANT_docs_from_prompt(prompt,document_store=None,retriever=None):
        """
        
        Função que realiza a pesquisa através da prompt especifica para a base de dados vetorial.

        Realiza o embedding da prompt, obtem os resultados e coloca-os sob a forma de texto novamente.

        Mantive fora da classe para poder testar separadamente sem ter de instanciar.

        
        """
        if not document_store:
            document_store=get_qdrant_store()
        if not retriever:
            retriever = QdrantEmbeddingRetriever(document_store=document_store)

        query_pipeline = Pipeline()
        query_pipeline.add_component("text_embedder", SentenceTransformersTextEmbedder())
        query_pipeline.add_component("retriever", retriever)
        query_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")

        query = prompt

        result = query_pipeline.run({"text_embedder": {"text": query}})
        return result



@component
class QdrantSearch:  
    """
    
    Componente para fazer a pesquisa na base de dados vetorial e guardar os resultados no dicionário prompt_mod

    """
    
    # @component.output_types(prompt=Dict)
    # def run(self,  prompt: Dict):  
    #     """
    #     
    #     Função que obtem a prompt especifica para esta pesquisa, chama a função para fazer a pesquisa e
    #     guarda o resultado e o score.
    #   
    #     """
    #     vector_prompt = prompt.get("vector_prompt", "")  
    #     if not vector_prompt:  
    #         raise ValueError("O dicionário de entrada não contém a chave 'vector_prompt'.")  
    #     search_results = get_QDRANT_docs_from_prompt(vector_prompt)  
    #     prompt["vector_search_result"] = search_results['retriever']['documents'][0].content
    #     prompt["vector_search_score"] = search_results['retriever']['documents'][0].score  
    #     return {"prompt":prompt}  



    @component.output_types(prompt_mod=Dict)  
    def run(self, prompt_mod: Dict):
        """
        
        Função que obtem a prompt especifica para esta pesquisa, chama a função para fazer a pesquisa.

        Concatena todos os resultados com score superior a 0.45 e guarda. 
        Guarda a média dos scores dos resultados concatenados.
        
        """  
        keyword_prompt = prompt_mod.get("vector_prompt", "")  
        if not keyword_prompt:  
            raise ValueError("O dicionário de entrada não contém a chave 'vector_prompt'.")  
        
        search_results = get_QDRANT_docs_from_prompt(keyword_prompt)  
        
        # Filtrando documentos com score maior que 0.45  
        filtered_documents = [  
            doc  
            for doc in search_results['retriever']['documents']  
            if doc.score > 0.45  
        ]  
        
        # Obtendo os conteúdos dos documentos filtrados  
        filtered_contents = [doc.content for doc in filtered_documents]  
        
        # Calculando o score médio dos documentos filtrados  
        if filtered_documents:  
            average_score = sum(doc.score for doc in filtered_documents) / len(filtered_documents)  
        else:  
            average_score = 0  # ou outro valor apropriado caso não haja documentos  
        
        prompt_mod["vector_search_results"] = filtered_contents  
        prompt_mod["vector_search_score"] = average_score  
        
        return {"prompt_mod":prompt_mod}




def get_Osearch_docs_from_prompt(prompt,document_store=None,retriever=None):
        """

        Função que realiza a pesquisa através da prompt especifica para a base de dados por keywords.

        Mantive fora da classe para poder testar separadamente sem ter de instanciar.

        """
        if not document_store:
            document_store=get_Osearch_store()
        if not retriever:
            retriever = OpenSearchBM25Retriever(document_store=document_store)
        query_pipeline = Pipeline()
        query_pipeline.add_component("retriever", retriever)
        query = prompt
        result = query_pipeline.run({"retriever": {"query": query}})
        return result


@component
class OpenSearch():  
    """
    
    Componente para fazer a pesquisa na base de dados OpenSearche guardar os resultados no dicionário prompt_mod

    """


    @component.output_types(prompt_mod=Dict)
    def run(self,  prompt_mod: Dict):
        """
        
        Função que obtem a prompt especifica para esta pesquisa, chama a função para fazer a pesquisa e
        guarda o resultado e o score.
        
        """  
        keyword_prompt = prompt_mod.get("vector_prompt", "")  
        if not keyword_prompt:  
            raise ValueError("O dicionário de entrada não contém a chave 'vector_prompt'.")  
        search_results = get_Osearch_docs_from_prompt(keyword_prompt)  
        prompt_mod["keyword_search_result"] = search_results['retriever']['documents'][0].content
        prompt_mod["keyword_search_score"] = search_results['retriever']['documents'][0].score  
        return {"prompt_mod": prompt_mod}  
