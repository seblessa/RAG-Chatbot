from haystack import component
from typing import Dict, List
import json
import os
from openai import AzureOpenAI

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
        endpoint = os.getenv("ENDPOINT_URL", "https://toolkit-sc.openai.azure.com/")
        deployment = os.getenv("DEPLOYMENT_NAME","Cheap")

        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=os.getenv("DEPLOYMENT_KEY"),
            api_version="2024-05-01-preview",
        )
        completion = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "system", "content": sys},{"role": "system", "content": msg_context}] +
                     prompt,
            max_tokens=1800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False
        )
        # print([{"role": "system", "content": sys},{"role": "system", "content": msg_context}] +
        #              prompt)
        response_content = completion.choices[0].message.content
        return response_content

    def build_context(self,context):
        return

    @component.output_types(response=Dict)
    def run(self, prompt: List, context:Dict):
        grouped_context=group_documents(context["used_context"]["selected_documents"])
        grouped_context_str=json.dumps(grouped_context,ensure_ascii=False)
        response = self.generate(prompt, grouped_context_str)
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