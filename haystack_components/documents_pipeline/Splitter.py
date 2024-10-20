from llmsherpa.readers import LayoutPDFReader
from typing import List
from haystack import  Document, component
from pathlib import Path
# import logging
import hashlib

@component
class LayoutPDFSplitter():  
    
    """
    
    Componente que usa o LayoutPDFReader do LLMSherpa para dividir o documento em secções.

    Para cada secção a função analisa a TAG e agrupa o Header com as tags não header seguintes até ao proximo header e assim sucessivamente gerando secções processadas.

    Para cada secção processada é gerado um documento com o id único, o texto e um campo de metadados com o filepath e o número da página, posteriormente vão ser adicionadas a este campo as métricas da classificação.

    """
    
    @component.output_types(documents=List[Document])
    def run(self, sources: List[Path], doc_id, return_json=False):  
        pdf_reader = LayoutPDFReader("http://localhost:5010/api/parseDocument?renderFormat=all&useNewIndentParser=true")  
        print("reading PDF")
        doc = pdf_reader.read_pdf(sources[0])  
  
        resultados = []  
        texto_atual = ""  
        print("Parsing PDF")
        # return {"result":doc}
        # print(doc.json)
        if return_json:
            return {"result":doc.json}
        formatted_documents = [] 
        for item in doc.json:
            page_idx=item["page_idx"]
            if item['tag'] != 'para' or item['tag'] == 'header':  
                if texto_atual:  
                    document = Document(  
                        id=hashlib.sha256(texto_atual.encode()).hexdigest(),
                        content=texto_atual,
                        meta={  
                            "file_path": str(sources[0]),  
                            "page_number": page_idx + 1,  
                            "split_id": page_idx,  
                            "split_idx_start": 0,  # Assuming starting index is 0 for each split 
                            "parent_doc_id":doc_id
                        }  
                    )  
                    formatted_documents.append(document) 

                texto_atual = ' '.join(item['sentences'])  
            else:  
                texto_atual += ' ' + ' '.join(item['sentences'])  
  
        # Adiciona o último texto processado  
        if texto_atual:  
            document = Document(  
                id=hashlib.sha256(texto_atual.encode()).hexdigest(),
                content=texto_atual,
                meta={  
                    "file_path": str(sources[0]),  
                    "page_number": page_idx + 1,  
                    "split_id": page_idx,  
                    "split_idx_start": 0,  # Assuming starting index is 0 for each split 
                    "parent_doc_id":doc_id
                }  
            )  
            formatted_documents.append(document) 
        print("PDF parsed")
        return {"documents": formatted_documents}