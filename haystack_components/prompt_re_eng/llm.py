from haystack import component
from typing import Dict
import json  
import os
from openai import AzureOpenAI


# Prompt de sistema para transformar a prompt do user em duas prompts distintas uma para keywords e outra para pesquisa vetorial

sys = '''
        Você é um assistente altamente eficiente especializado em transformar perguntas de utilizadores em duas consultas otimizadas: uma para pesquisa por keywords em bases de dados OpenSearch e outra para pesquisa vetorial em bases de dados Qdrant. A sua tarefa é pegar na pergunta original do utilizador e gerar duas consultas que maximizem a relevância dos resultados.  
        Nota que receberás um historico da conversa de forma a poderes especificar melhor os parametros de pesquisa.
        - Para a consulta por keywords, foque-se nas palavras-chave mais importantes.  
        - Para a consulta vetorial, capture a essência semântica da pergunta.  
  
        Certifique-se de que ambas as consultas resultantes são claras, concisas e diretamente relacionadas à intenção do utilizador.  
          
        Devolve as perguntas modificadas em formato JSON com as chaves "keyword_prompt" e "vector_prompt". Nunca podes enviar listas vazias.
        formato da resposta: {"vector_prompt":["string de pesquisa 1","string de pesquisa 2", "mais strings de pesquisa"],"keyword_prompt":[["grupo1_string1","grupo1_string2","grupo1_string3"],["grupo2_string1","grupo2_string2",],[outros grupos]]}
        Assegura-te que envias um JSON valido
    '''

msg_history_example='''
                {"role": "user", "content": "Existe a possibilidade da empresa soferer ataques de cibersegurança?"}
                {"role": "assistant", "content": "Sim, existe sempre uma possibilidade da empresa sofrer ataques te diferentes tipos." }
                {"role": "user", "content": "Quais são as ameaças de cibersegurança mais comuns?"}
'''
examples=[
        {"role": "user", "content": msg_history_example},
        {"role": "assistant", "content": '''{"vector_prompt":["ameaças cibersegurança comuns","ameaças segurança cibernética","cibersegurança riscos comuns","ameaças comuns cibersegurança","segurança cibernética ameaças frequentes"],"keyword_prompt":[["ameaças","cibersegurança","comuns"],["ameaças","segurança cibernética"],["cibersegurança","riscos comuns"]]}'''}  
]

@component
class LLMPrompt:  
    
    """
    
    Classe que usa um modelo gpt3.5 azure-openai para modificar a prompt do utilizador e devolver um json com duas prompts distintas uma para a pesquisa vetorial e outra para a pesquisa por keywords.

    Retorna um dicionário prompt_mod que contem a prompt original e as duas prompts novas e que posteriormente vai conter os resultados e os scores.

    
    """
    

    @component.output_types()
    def generate(self, text):  
        endpoint = os.getenv("ENDPOINT_URL", "https://toolkit-sc.openai.azure.com/")  
        # deployment = os.getenv("DEPLOYMENT_NAME", "Geral")
        deployment = os.getenv("DEPLOYMENT_NAME", "Cheap")
  
        client = AzureOpenAI(  
            azure_endpoint=endpoint,  
            api_key=os.getenv("DEPLOYMENT_KEY"),
            api_version="2024-05-01-preview",  
        )  
        completion = client.chat.completions.create(  
            model=deployment,  
            messages=[  
                {"role": "system", "content": sys}]+
                examples+
                [{"role": "user", "content": text}],  
            max_tokens=800,  
            temperature=0.7,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0,  
            stop=None,  
            stream=False  
        )  
          
        response_content = completion.choices[0].message.content  
        return response_content
    
    @component.output_types(prompt_mod=Dict)  
    def run(self, user_prompt: str):
        response=None
        while response is None:
            response = self.generate(user_prompt)
            
            try:
                response_json = json.loads(response)  
            except:  
                response = None
                continue
            
            
            keyword_prompts = response_json.get("keyword_prompt", [])
            if not keyword_prompts or not isinstance(keyword_prompts, list):
                response = None 
                continue
            
        
            vector_prompts = response_json.get("vector_prompt", [])
            if not vector_prompts or not isinstance(vector_prompts, list):
                response = None 
                continue

            break
  
        # Assumindo que a resposta do LLM será um JSON válido
        print(f"PROMPT RE_ENGI: {response}")
        response_json = json.loads(response)  
        print(f"NEW QUERY: {response_json}")
        return {"prompt_mod":{  
            "original_prompt": user_prompt,  
            "keyword_prompt": response_json.get("keyword_prompt"),  
            "vector_prompt": response_json.get("vector_prompt")  
        } }