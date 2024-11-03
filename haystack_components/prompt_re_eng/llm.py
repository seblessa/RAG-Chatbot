from haystack import component
from typing import Dict
import json  
import os
from openai import AzureOpenAI

from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig
import torch

from huggingface_hub import InferenceClient

API_KEY= "CHANGE IT"

# Prompt de sistema para transformar a prompt do user em duas prompts distintas uma para keywords e outra para pesquisa vetorial

sys = '''
You are a highly efficient assistant specialized in transforming user questions into two optimized queries: one for keyword search in OpenSearch databases and another for vector search in Qdrant databases. Your task is to take the user's original question and generate two queries that maximize the relevance of the results.
Note that you will receive a conversation history to better specify the search parameters.

For the keyword query, focus on the most important keywords.
For the vector query, capture the semantic essence of the question.
Ensure that both resulting queries are clear, concise, and directly related to the user's intent.

Return the modified questions in JSON format with the keys "keyword_prompt" and "vector_prompt." You must never send empty lists.
Response format: {"vector_prompt":["search string 1","search string 2", "more search strings"],"keyword_prompt":[["group1_string1","group1_string2","group1_string3"],["group2_string1","group2_string2"],[other groups]]}
Make sure to send a valid JSON.
    '''
msg_history_example='''  
                {"role": "user", "content": "Is there a possibility of the company suffering from cybersecurity attacks?"}  
                {"role": "assistant", "content": "Yes, there is always a possibility of the company facing attacks of different types."}  
                {"role": "user", "content": "What are the most common cybersecurity threats?"}  
'''  
examples=[  
        {"role": "user", "content": msg_history_example},  
        {"role": "assistant", "content": '''{"vector_prompt":["common cybersecurity threats","cybersecurity threats","common risks of cybersecurity","frequent cybersecurity threats","cybersecurity threats"],"keyword_prompt":[["threats","cybersecurity","common"],["threats","cybersecurity"],["cybersecurity","common risks"]]}'''}  
]  


@component
class LLMPrompt:  
    
    """
    
    modificar a prompt do utilizador e devolver um json com duas prompts distintas uma para a pesquisa vetorial e outra para a pesquisa por keywords.

    Retorna um dicionário prompt_mod que contem a prompt original e as duas prompts novas e que posteriormente vai conter os resultados e os scores.

    
    """


    def answer_question(self, question, max_length=1000, temperature=0.7):
        client = InferenceClient(api_key=API_KEY)

        messages=[{"role": "system", "content": sys}]+ examples+[{"role": "user", "content": question}]

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
        
    @component.output_types(prompt_mod=Dict)
    def run(self, user_prompt: str):
        max_attempts = 3  # Define o número máximo de tentativas
        attempts = 0
        response = None

        while attempts < max_attempts:
            response = self.answer_question(user_prompt)
            print(response)

            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                response = None
                attempts += 1
                continue

            keyword_prompts = response_json.get("keyword_prompt", [])
            vector_prompts = response_json.get("vector_prompt", [])

            if not (isinstance(keyword_prompts, list) and isinstance(vector_prompts, list)):
                response = None
                attempts += 1
                continue

            # Se a resposta for válida, sai do loop
            break
        else:
            # Se atingir o número máximo de tentativas, retorna a prompt original formatada
            return {
                "prompt_mod": {
                    "original_prompt": user_prompt,
                    "keyword_prompt": [user_prompt],
                    "vector_prompt": [user_prompt]
                }
            }

        # Assumindo que a resposta do LLM será um JSON válido
        print(f"PROMPT RE_ENGI: {response}")
        response_json = json.loads(response)
        print(f"NEW QUERY: {response_json}")
        return {
            "prompt_mod": {
                "original_prompt": user_prompt,
                "keyword_prompt": response_json.get("keyword_prompt"),
                "vector_prompt": response_json.get("vector_prompt")
            }
        }
