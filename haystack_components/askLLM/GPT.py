from haystack import component
from typing import Dict, List
import json
import os
from openai import AzureOpenAI

from huggingface_hub import InferenceClient

from transformers import AutoTokenizer

# Carrega o tokenizer do modelo que estás a usar. Substitui pelo modelo desejado, ex: 'bert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")


sys = '''
        You are a highly efficient assistant specialized in answering questions related to the provided context.

You should use only the provided context to answer questions;
When it does not contain the necessary information to respond, you should ask for more information or state that this information is not in your database.
Always use markdown in your response.
    '''
examples = []

@component
class ASK_LLM:
    """

    Classe que usa um modelo gpt3.5 azure-openai para modificar a prompt do utilizador e devolver um json com duas prompts distintas uma para a pesquisa vetorial e outra para a pesquisa por keywords.

    Retorna um dicionário prompt_mod que contem a prompt original e as duas prompts novas e que posteriormente vai conter os resultados e os scores.


    """

    @component.output_types()
    def generate(self, prompt, msg_context):

        client = InferenceClient(api_key="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")
        joined=" ".join(msg_context)
        print(msg_context)
        messages=[{"role": "system", "content": sys}]+[{"role": "user", "content": joined}] + [{"role": "user", "content":prompt}]
        

        stream = client.chat.completions.create(
            model="meta-llama/Llama-3.2-1B-Instruct", 
            messages=messages, 
            temperature=0.5,
            max_tokens=1024,
            top_p=0.7,
            stream=True
        )

        full_response = ""

        # Iterar sobre cada chunk, acumulando o conteúdo
        for chunk in stream:
            full_response += chunk.choices[0].delta.content  # ou "text", dependendo da estrutura do chunk

        # Imprimir toda a resposta junta
        return full_response

    def build_context(self,context):
        return

    @component.output_types(response=Dict)
    def run(self, prompt: List, context): 
        conteudo = [doc.content for doc in context['JoinDocuments']['documents']]       
        conteudo=get_limited_context(context)
        
        response = self.generate(prompt, conteudo)
        return {"response":response}


def get_limited_context(context):
    conteudo = [doc.content for doc in context['JoinDocuments']['documents']]
    token_counts = [len(tokenizer.tokenize(text)) for text in conteudo]
    
    print("Número de tokens em cada documento:", token_counts)
    print("Total de tokens:", sum(token_counts))

    limited_context = []
    total_tokens = 0

    for text, count in zip(conteudo, token_counts):
        # Verifica se adicionar o próximo documento ultrapassará o limite
        if total_tokens + count <= 4000:
            limited_context.append(text)
            total_tokens += count
        else:
            break  # Sai do loop se o limite for alcançado

    print("Número total de tokens após limitação:", total_tokens)
    return limited_context