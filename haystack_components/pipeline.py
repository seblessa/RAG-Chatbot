from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.opensearch import OpenSearchDocumentStore
from haystack_integrations.components.retrievers.opensearch import OpenSearchBM25Retriever,OpenSearchEmbeddingRetriever
from haystack import Pipeline
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter, TextCleaner

from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder

from documents_pipeline.classifiers import NamedEntityExtractor,IntentExtractor,LLMExtractor, LLMExtractorAzure

from documents_pipeline.Splitter import LayoutPDFSplitter


from prompt_re_eng.llm import LLMPrompt
# from .prompt_re_eng.search_stores import QdrantSearch,OpenSearch,get_Osearch_docs_from_prompt,get_QDRANT_docs_from_prompt
from documents_pipeline.save_stores import get_Osearch_store,get_qdrant_store,save_docs_to_Osearch,save_docs_to_QDRANT
from prompt_re_eng.new_search import QdrantSearch, OpenSearch, JoinDocuments#, SentenceTransformersRanker
from askLLM.GPT import ASK_LLM
import time


def document_processor_pipeline(doc_path,doc_id):  
    """
    Processa e guarda um documento nas bases de dados.

    As linhas comentadas correspondem à forma default de fazer chunck do haystack.

    Parser Personalidado do LLMSherpa -> LLM que extrai NER e INTENT -> Guarda OpenSearch -> Divide em frases  -> Guarda QDrant
    
    """
    
    
    p = Pipeline()  
    # p.add_component("PDFconverter", PyPDFToDocument())  
    # p.add_component("DocCleaner", DocumentCleaner())  
    # p.add_component("Splitter", DocumentSplitter())  
    p.add_component("Splitter",LayoutPDFSplitter())

    # p.add_component("LLM",LLMExtractor())
    # p.add_component("LLM",LLMExtractorAzure())
    
    # p.add_component("Save_OS",save_docs_to_Osearch())
    # p.add_component("Split_Sent",DocumentSplitter(split_by="sentence", split_length=3, split_overlap=0))
    # p.add_component("Save_QD",save_docs_to_QDRANT())

    # # p.connect("PDFconverter", "DocCleaner")  
    # # p.connect("DocCleaner", "Splitter") 

    # p.connect("Splitter","LLM")
    # p.connect("LLM","Save_OS")
    # p.connect("Save_OS","Split_Sent")
    # p.connect("Split_Sent","Save_QD")
    
      
    # res = p.run({"PDFconverter": {"sources": [doc_path]}})
    res = p.run({"Splitter": {"sources": [doc_path],"doc_id":doc_id}})

    return res 

def new_doc_pipeline(doc_path,doc_id):
    p = Pipeline()
    p.add_component("Splitter",LayoutPDFSplitter())
    p.add_component("LLM",LLMExtractorAzure())

    p.add_component("Save_OS", save_docs_to_Osearch())
    p.add_component("Split_Sent", SectionToPhrasesSplit())
    p.add_component("Save_QD", save_docs_to_QDRANT())


    p.connect("Splitter","LLM")
    p.connect("LLM","Save_OS")
    p.connect("Save_OS","Split_Sent")
    p.connect("Split_Sent","Save_QD")
    res=p.run({"Splitter": {"sources": [doc_path],"doc_id":doc_id}})
    return res

def pdf_layout_process(file,doc_id):
    p = Pipeline()  
    
    p.add_component("Splitter",LayoutPDFSplitter()) 
    res = p.run({"Splitter": {"sources": [file],"doc_id":doc_id,"return_json":True}})

    return res 

def prompt_engineering_pipeline(prompt):  
    """  
    Cria um dicionário com todas as informações relevantes para a pesquisa.  
    user_prompt -> LLM para otimizar a prompt para cada base de dados -> Pesquisa QDrant -> Pesquisa OpenSearch -> Combinação dos resultados  
    Formato final do dicionário prompt_mod:  
    {'original_prompt': '...', 'keyword_prompt': '...', 'vector_prompt': '...', 'vector_search_results': ... , 'vector_search_score': ... , 'keyword_search_result': ... , 'keyword_search_score': ...}  
    Posteriormente este dicionário vai ser dado a um LLM para ele conseguir responder à pergunta do user com este contexto extra.  
    """  
    join_documents = JoinDocuments(join_mode="distribution_based_rank_fusion")  
    # rerank = SentenceTransformersRanker(model_name_or_path="cross-encoder/ms-marco-MiniLM-L-6-v2")
    p = Pipeline()  
    p.add_component("LLM",LLMPrompt())  
    p.add_component("VS",QdrantSearch())  
    p.add_component("KS",OpenSearch())  
    p.add_component("JoinDocuments",join_documents)
    # p.add_component("JoinDocuments",new_joiner)
    # p.add_component("ReRanker",rerank)  

    p.connect("LLM", "VS")  
    p.connect("LLM", "KS")  
    p.connect("VS", "JoinDocuments")
    p.connect("KS", "JoinDocuments")
    res = p.run({"user_prompt": prompt})  
    # print(res)  
    return res  
  

def ask_LLM_with_context(prompt,context):
    p = Pipeline()
    p.add_component("LLM", ASK_LLM())
    res=p.run({"prompt": prompt,"context":context})
    return res

## Usage

## Load and save pdf document
# start=time.time()


mydoc=document_processor_pipeline("sample.pdf",1)
print(mydoc)


# print(time.time()-start)



## Test query retrieval from DB

# prompt="O IVA está incluido?"

## Using Pipeline

# res=prompt_engineering_pipeline(prompt)

## Manually 

# res_O=get_Osearch_docs_from_prompt(prompt)
# res_Q=get_QDRANT_docs_from_prompt(prompt)

# print(res_O.get("retriever").get("documents")[0].content)
# print(res_O.get("retriever").get("documents")[0].score)

# print("--"*40)

# print(res_Q['retriever']['documents'][0].content)
# print(res_Q['retriever']['documents'][0].score)