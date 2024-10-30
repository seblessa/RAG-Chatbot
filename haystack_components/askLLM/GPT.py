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
        Tu és um assistente altamente eficiente especializado em responder a perguntas relacionadas com o contexto fornecido.  
        
        Deves usar apenas o contexto fornecido para responder a perguntas;
        Quando este não tiver a informação necessária para responder, deves pedir mais informações ou dizer que essa informação não consta na tua base de dados
        Responde sempre em Português de portugal (europeu).
        Usa sempre markdown na tua resposta.
    '''
examples = []
MAX_CONTEXT_TOKENS=int(os.getenv("MAX_CONTEXT_TOKENS",4000))
@component
class ASK_LLM:
    """

    Classe que usa um modelo gpt3.5 azure-openai para modificar a prompt do utilizador e devolver um json com duas prompts distintas uma para a pesquisa vetorial e outra para a pesquisa por keywords.

    Retorna um dicionário prompt_mod que contem a prompt original e as duas prompts novas e que posteriormente vai conter os resultados e os scores.


    """

    @component.output_types()
    def generate(self, prompt, msg_context):

        client = InferenceClient(api_key="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")

        messages=[{"role": "system", "content": sys}]+[{"role": "user", "content": msg_context}] + [{"role": "user", "content":prompt}]
        
        # print("Número de tokens em cada documento:", token_counts)
        # print("Total de tokens:", sum(token_counts))
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
        response = self.generate(prompt, conteudo)
        return {"response":response}


from collections import defaultdict


def group_documents(selected_documents):
    grouped = defaultdict(lambda: defaultdict(list))
    used_tokens=0
    for doc in selected_documents:
        section = doc['section']
        section_id = section['id']
        score = doc['score']

        page = section['parent']
        page_number = page['page_number']

        parent_doc = page['parent']
        parent_id = parent_doc['id']
        filename = parent_doc['filename']

        grouped[filename][page_number].append({
            "score": score,
            'section_id': section_id,
            'raw_content': section['raw_content']
            # 'extracted_information': section['extracted_information']
        })
        used_tokens+=section["num_tokens"]
        if used_tokens >= MAX_CONTEXT_TOKENS:
            return grouped
    return grouped