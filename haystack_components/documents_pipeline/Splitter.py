from llmsherpa.readers import LayoutPDFReader
from typing import List, Dict
from haystack import  Document, component
from pathlib import Path
# import logging
import hashlib
from pdf_processor.document_processor import dict_to_DB


@component
class LayoutPDFSplitter():  
    
    """
    
    Componente que usa o LayoutPDFReader do LLMSherpa para dividir o documento em secções.

    Para cada secção a função analisa a TAG e agrupa o Header com as tags não header seguintes até ao proximo header e assim sucessivamente gerando secções processadas.

    Para cada secção processada é gerado um documento com o id único, o texto e um campo de metadados com o filepath e o número da página, posteriormente vão ser adicionadas a este campo as métricas da classificação.

    """
    
    @component.output_types(documents=List[Dict])
    def run(self, sources: List[Path], doc_id):
        pdf_doc=dict_to_DB(sources[0])


        doc_sections=pdf_doc.get_partitioned_PDF_dict()

        doc_sections["sections"]=[]

        for section in doc_sections["content"]:
            text=section["content"]
            page_num=section["pages"][0]
            document = Document(
                id=hashlib.sha256(text.encode()).hexdigest(),
                content=text,
                meta={
                    "file_path": str(sources[0]),
                    "page_number": page_num,
                    "parent_doc_id": doc_id
                }
            )
            doc_sections["sections"].append(document)
        return {"documents": doc_sections}

from haystack import Pipeline
from haystack.components.preprocessors import DocumentSplitter
@component
class SectionToPhrasesSplit():
    @component.output_types(documents=List[Dict])
    def run(self, documents:List[Dict],):
        docs=documents["sections"]
        p = Pipeline()
        p.add_component("Splitter",DocumentSplitter(split_by="sentence", split_length=3, split_overlap=0))
        res = p.run({"Splitter": {"documents": docs}})
        docs=res["Splitter"]["documents"]
        documents["phrases"]=docs
        return {"documents": documents}