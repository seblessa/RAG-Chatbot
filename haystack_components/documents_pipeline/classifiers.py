import torch
from typing import List
from transformers import pipeline  
from huggingface_hub import login 
from haystack import Document, component
from datasets import Dataset
from transformers.pipelines.pt_utils import KeyDataset
import time
import json
import spacy

@component
class NamedEntityExtractor: 
    """
    
    Classe capaz de fazer NER com modelos do spacy, o download necessita de ser feito previamente usando: $ python -m spacy download MODEL

    """ 
    def __init__(self, backend="spacy", model="en_core_web_sm"):  
        import spacy  
        self.nlp = spacy.load(model)  
    
    @component.output_types(documents=List[Document])       
    def run(self,  texts: List[Document]):  
        print(texts)
        entities = []  
        for doc in texts:  
            # Extrai o texto do campo 'content' do documento
            text = doc.content
            
            # Processa o texto usando o NLP
            nlp_doc = self.nlp(text)  
            
            # Extrai as entidades e adiciona ao campo 'meta'
            doc_ents = [(ent.text, ent.label_) for ent in nlp_doc.ents]  
            entities.append(doc_ents)
            
            # Atualiza o campo 'meta' com as entidades extraídas
            if 'entities' not in doc.meta:
                doc.meta['entities'] = doc_ents
            else:
                doc.meta['entities'].extend(doc_ents)

        return {'documents': texts}  
  
class IntentExtractor:  
    """
    Classe capaz de fazer extração de intenções com modelos do Huggingface Transformers
    e modelos do spaCy para NER. O download do modelo do spaCy e do Transformers 
    necessita ser feito previamente.
    """

    def __init__(self, ner_model_name: str = "en_core_web_sm"):  
        # Carrega o modelo para a extração de intenções via Transformers
        self.intent_pipeline = pipeline("text-classification", ner_model_name)
        
        # Carrega o modelo de NER do spaCy
        self.nlp = spacy.load(ner_model_name)
    
    @component.output_types(documents=List[Document])
    def run(self, texts: List[Document]):  
        # Listas para armazenar entidades e intenções extraídas
        intents = []
        entities = []
        
        # Processa cada documento
        for doc in texts:  
            text_content = doc.content

            # Extração de intenções
            intent_result = self.intent_pipeline(text_content)  
            intent = intent_result[0]['label']
            intents.append(intent)
            
            # Adiciona a intenção ao campo meta do documento
            if 'intent' not in doc.meta:
                doc.meta['intent'] = intent
            else:
                doc.meta['intent'] += ", " + intent

            # Extração de entidades usando spaCy
            spacy_doc = self.nlp(text_content)
            doc_entities = [(ent.text, ent.label_) for ent in spacy_doc.ents]
            entities.append(doc_entities)
            
            # Adiciona as entidades ao campo meta do documento
            if 'entities' not in doc.meta:
                doc.meta['entities'] = doc_entities
            else:
                doc.meta['entities'].extend(doc_entities)

        return {'documents': texts}
