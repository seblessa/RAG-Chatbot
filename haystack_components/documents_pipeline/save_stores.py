
from typing import  List

from haystack import Document, component
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from haystack_integrations.document_stores.opensearch import OpenSearchDocumentStore
from haystack.document_stores.types import DuplicatePolicy

from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder



def get_qdrant_store():
    """

    Função que localiza a qdrant store a correr no docker.

    ATENÇÃO à linha recreate_index, descomentar apenas caso seja para fazer nova indexação

    """
    
    document_store = QdrantDocumentStore(
    url="localhost",
    index="Document",
    embedding_dim=768,
    # recreate_index=True, # This will delete ALL existing documents
    hnsw_config={"m": 16, "ef_construct": 64}  # Optional
)
    return document_store

 
def get_Osearch_store():
    """

    Função que retorna a OpenSearch Store

    """
    
    return OpenSearchDocumentStore(http_auth=("admin","Master_pw_123!#"), use_ssl=True)
#set OPENSEARCH_INITIAL_ADMIN_PASSWORD=Master_pw_123!#

@component
class save_docs_to_Osearch():
    """

    Função que guarda os documentos na base de dados OpenSearch.


    """
    
    @component.output_types(documents=List[Document])
    def run(self, documents:List[Document],document_store=None):
        if not document_store:
            document_store=get_Osearch_store()
        document_store.write_documents(documents,policy=DuplicatePolicy.OVERWRITE)
        # print(documents)
        return {"documents":documents}



@component
class save_docs_to_QDRANT():
    """

    Função que guarda os documentos na base de dados QDRANT.

    Para guardar os documentos numa base de dados vetorial precisamos de criar os embeddings desses documentos.

    Depois de iniciar o embedder e de ter os embedduings  dos documentos guardamos na base de dados.

    """
    @component.output_types(documents=List[Document])
    def run(self, documents:List[Document],document_store=None,embedder=None):
        if not document_store:
            document_store=get_qdrant_store()
        if not embedder:
            embedder=SentenceTransformersDocumentEmbedder()
        embedder.warm_up()
        embedded_docs=embedder.run(documents)
        document_store.write_documents(embedded_docs.get("documents"),policy=DuplicatePolicy.OVERWRITE)
        # print(embedded_docs)
        return {"documents":documents}
    


def get_all_document_ids(document_store=None):  
    """

    Função que faz pesquisas sem critério para obter todos os documentos disponiveis.

    Retorna os id's desses documentos e é chamada inúmeras vezes pela função delete_documents_from_opensearch porque a pesquisa nunca retorna TODOS os documentos de uma vez.
    
    """
    
    if not document_store:  
        document_store = get_Osearch_store()  
      
    # Buscar todos os documentos usando _search_documents sem o objeto body  
    documents = document_store._search_documents(query={"match_all": {}})  
      
    # Extrair os IDs dos documentos  
    document_ids = [doc.id for doc in documents]  
    return document_ids  



# #This will delete ALL existing documents
def delete_documents_from_docStore(document_store=None,docId=None):  
    """
    
    Função para eliminar documentos da base de dados OpenSearch.

    Enquanto a função get_all_documents_ids retornar id's este script vai apagar os documentos correspondentes.

    Caso a função seja chamada com a variável all=True, vai necessitar também da variável docID e vai eliminar APENAS esse documento em especifico.
    
    """
    

    if not document_store:  
        document_store = get_Osearch_store()  
    if not docId:
        ids=get_all_document_ids(document_store)
        while ids!=[]:
            document_store.delete_documents(ids)
            ids=get_all_document_ids()  
    else: document_store.delete_documents(docId)  

def get_os_doc(oid, document_store=None):
    if not document_store:  
        document_store = get_Osearch_store() 
    docs=document_store.filter_documents({"id":oid})
    if docs:
        return docs[0]
    raise "No document found"

def delete_Qdrant_doc(doc_id):
    document_store=get_qdrant_store()
    document_store.delete_documents([doc_id])
    return
def delete_Osearch_doc(doc_id):
    document_store=get_Osearch_store()
    document_store.delete_documents([doc_id])
    return
