import torch
from typing import List, Dict
from transformers import pipeline  
from huggingface_hub import login 
from haystack import Document, component
from datasets import Dataset
from transformers.pipelines.pt_utils import KeyDataset
import time
import json

class NamedEntityExtractor: 
    """
    
    Classe capaz de fazer NER com modelos do spacy, o download necessita de ser feito previamente usando: $ python -m spacy download MODEL

    """ 
    def __init__(self, backend="spacy", model="pt_core_news_lg"):  
        import spacy  
        self.nlp = spacy.load(model)  
            
    def run(self, texts):  
        entities = []  
        for text in texts:  
            doc = self.nlp(text)  
            entities.append([(ent.text, ent.label_) for ent in doc.ents])  
        return entities  
  
  
class IntentExtractor:  
    """
    
    Classe capaz de fazer extração de intenções com modelos do spacy, o download necessita de ser feito previamente usando: $ python -m spacy download MODEL

    """ 


    def __init__(self, model_path):  
        from transformers import pipeline  
        self.intent_pipeline = pipeline("text-classification", model=model_path)  
      
    def run(self, texts):  
        intents = []  
        for text in texts:  
            result = self.intent_pipeline(text)  
            intents.append(result[0]['label'])  
        return intents  
    


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
      
    @component.output_types(documents=List[Dict])
    def run(self, documents: List[Dict]):

        endpoint = "https://toolkit-sc.openai.azure.com/"
        deployment = "Geral"  
  
        client = AzureOpenAI(  
            azure_endpoint=endpoint,  
            api_key="54f193ebbcec4af6ab0b3239d2e8e6f5",  
            api_version="2024-05-01-preview",  
        )  
        print("Azure OpenAI API setup completed")  

          
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
        # Process the dataset in batches  
        all_results = []  
        print("RUNNING query")  
        query_start = time.time()
        for doc in documents["sections"]:
            js = None
            tries=0
            example=doc.content
            while js is None and example != "" and example and len(example)>10 and tries<5:
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
                    js=json.loads(completion.choices[0].message.content)
                    doc.meta["extracted_info"] = json.dumps(js, ensure_ascii=False)
                except:
                    print(f"Failed to parse json: {completion.choices[0].message.content}, original_ content: {example}")
                    time.sleep(3**tries)
                    tries+=1
                    if tries == 5:
                        print(f"ERROR: Giving up on: {example}")

        print(f"query took: {time.time() - query_start}")

          
        print("LLM extractor finish")  
        return {"documents": documents}  
