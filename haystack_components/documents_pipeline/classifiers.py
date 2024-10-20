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

@component
class LLMExtractor:  
    
    """
    Classe para fazer extração de Intenção e NER com LLM Local usando Hugging Face Transformers.
    Transformo os pedaços de texto em dataset para ser mais eficiente no processamento.

    Para testar com outro modelo basta moficiar a variável "model".

    A resposta do LLM que vem no formato: NER: ... Intent:...
    
    No final essa resposta é adicionada ao campo no dicionário do documento. doc{..., "meta": {"exctracted_info":_______}
    
    """

    @component.output_types(documents=List[Document])
    def run(self,documents: List[Document]): 
        login("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")  
              
        if torch.cuda.is_available():  
            device = torch.device("cuda")  
            print(f"Using GPU: {torch.cuda.get_device_name(0)}")  
        else:  
            print("NOT using GPU")
            device = torch.device("cpu")  
    
        self.pipeline = pipeline(  
            "text-generation",  
            model="microsoft/Phi-3-mini-4k-instruct",  
            model_kwargs={"torch_dtype": torch.bfloat16},  
            device=device  
        )  

        print("LLM Model loaded")
    
        # Convert the list of documents to a dataset  
        # texts = [doc.content for doc in documents]  
        dataset = Dataset.from_list([{"text": doc.content} for doc in documents])
        print(f"DATASET: {dataset}")
    
        # Define the system message  
        system_message = '''És um assistente que fala em Português-Europeu(PT-PT) especializado em extração de intenções e reconhecimento de entidades nomeadas (NER) de textos fornecidos. 
                            Responda de forma direta, apenas com as informações extraídas, sem qualquer informação adicional. Dá respostas curtas. Formato da resposta: NER: .... Intenção: .... 
                            Exemplo: Texto: 'Gostava de reservar um voo para Paris na próxima terça-feira.' NER: [Paris:Local,terça-feira:Data] Intenção: Reservar voo'''  
    
        # Function to format input for the model  
        def format_input(example):  
            return {  
                "text": [  
                    {"role": "system", "content": system_message},  
                    {"role": "user", "content": example['text']}  
                ]  
            }  

        # Apply the function to the dataset  
        dataset = dataset.map(format_input)  
    
        # Process the dataset in batches  
        all_results = []  
        print("RUNNING query")
        query_start=time.time()
        for batch in self.pipeline(KeyDataset(dataset, "text"), batch_size=8, truncation="only_first", max_new_tokens=256):  
            all_results.extend(batch) 
        print(f"query took: {time.time()-query_start}") 
        print("formatting results")
        # Save the output to documents  
        for doc, result in zip(documents, all_results):  
            generated_text = result['generated_text'][-1]['content']  
            # doc['meta']["extracted_info"] = generated_text  
            doc.meta["extracted_info"] = generated_text  
        print("LLM extractor finish")
        return {"documents": documents}    
    

from openai import AzureOpenAI

@component
class LLMExtractorAzure:  
    """  
    Classe para fazer extração de Intenção e NER com GPT-3.5 Turbo via Azure OpenAI API.  
    Transformo os pedaços de texto em dataset para ser mais eficiente no processamento.  
    A resposta do LLM que vem no formato: NER: ... Intent:...  
    No final essa resposta é adicionada ao campo no dicionário do documento. doc{..., "meta": {"extracted_info":_______}  
    """  
      
    @component.output_types(documents=List[Document])  
    def run(self, documents: List[Document]):  

        endpoint = "https://toolkit-sc.openai.azure.com/"
        deployment = "Geral"  
  
        client = AzureOpenAI(  
            azure_endpoint=endpoint,  
            api_key="54f193ebbcec4af6ab0b3239d2e8e6f5",  
            api_version="2024-05-01-preview",  
        )  
        print("Azure OpenAI API setup completed")  
          
        # Convert the list of documents to a dataset  
        texts = [doc.content for doc in documents]  
        # dataset = Dataset.from_dict({"text": texts})  
          
        # Define the system message  
        system_message = '''És um assistente que fala em Português-Europeu(PT-PT) especializado em extração de intenções e reconhecimento de entidades nomeadas (NER) de textos fornecidos.  
                            Responda de forma direta, apenas com as informações extraídas, sem qualquer informação adicional. Dá respostas curtas. Formato da resposta: {"NER":[{"<palavra>":"<classificação>"},{"<palavra>":"<classificação>"},...], "Intenção": [<classificação de intenção>,...]}
                            A resposta deve ser um JSON valido.
                            '''  
          
        # Function to format input for the model  
        def format_input(example):  
            return {  
                "messages": [  
                    {"role": "system", "content": system_message},  
                    {"role": "user", "content": example['text']}  
                ]  
            }  
        examples=[
            {"role": "user", "content": "Gostava de reservar um voo para Paris na próxima terça-feira."},
            {"role": "assistant", "content": '''{"NER":[{"Paris":"Local"},{"terça-feira":"Data"}], "Intenção": ["Reservar voo"]}'''}, 
        ]
        # Apply the function to the dataset  
        # dataset = dataset.map(format_input)  
          
        # Process the dataset in batches  
        all_results = []  
        print("RUNNING query")  
        query_start = time.time()  
          
        for example in texts:
            # print(f"EXAMPLE MSG: {example}")
            completion = client.chat.completions.create(  
            model=deployment,  
            messages=[  
                {"role": "system", "content": system_message},  
            ]+examples+[{"role": "user", "content": example}],  
            max_tokens=800,  
            temperature=0.7,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0,  
            stop=None,  
            stream=False  
            )
            # print(f"GPT RESPONSE: {completion.choices}")
            try:
                all_results.append(json.loads(completion.choices[0].message.content))
            except:
                print(f"Failed to parse json: {completion.choices[0].message.content}")
                raise "Json could not be parsed."
          
        print(f"query took: {time.time() - query_start}")
        print("formatting results")  
          
        # Save the output to documents
        print(f"ALL RESULTS:\n {all_results}")
        for doc, result in zip(documents, all_results):  
            doc.meta["extracted_info"] = json.dumps(result, ensure_ascii=False)
          
        print("LLM extractor finish")  
        return {"documents": documents}  
