from haystack import component
from typing import Dict, List
import json
import os
from openai import AzureOpenAI

from huggingface_hub import InferenceClient

from transformers import AutoTokenizer


API_KEY= "CHANGE IT"


# Carrega o tokenizer do modelo que estás a usar. Substitui pelo modelo desejado, ex: 'bert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")


sys = '''
        You are a concise and highly efficient assistant specializing in answering questions based solely on the provided context.

- Only use the provided context to answer questions.
- If the context lacks the necessary information, briefly ask for more information or state that this information is not available.
- Always respond in plain text.
- Prioritize brevity: give the shortest possible answer that fully addresses the question.
- Limit responses to one or two sentences.

Example 1:
Q: What are the obligations of manufacturers under this regulation?
A:Manufacturers must ensure devices comply with safety and performance standards, conduct clinical evaluations, maintain technical documentation, and keep devices in conformity throughout their lifecycle.
Example 2:
Q:Who is responsible for regulatory compliance in a manufacturer’s organization?
A:A designated individual responsible for regulatory compliance, possessing specific qualifications in medical device regulation, must be available.
Example 3:
Q:What obligations do importers have under the regulation?
A:Importers must verify conformity, register devices, provide samples if required, and report risks.'''

examples = []

@component
class ASK_LLM:
    """

     modificar a prompt do utilizador e devolver um json com duas prompts distintas uma para a pesquisa vetorial e outra para a pesquisa por keywords.

    Retorna um dicionário prompt_mod que contem a prompt original e as duas prompts novas e que posteriormente vai conter os resultados e os scores.


    """

    @component.output_types()
    def generate(self, prompt, msg_context):

        client = InferenceClient(api_key=API_KEY)
        joined=" ".join(msg_context)    
        messages=[{"role": "system", "content": sys}]+[{"role": "system", "content": joined}] + [{"role": "user", "content": str(prompt) + "Respond with a brief, precise answer. Avoid unnecessary details and repetitions. Keep it within one or two sentences only."}]

        

        stream = client.chat.completions.create(
            model="meta-llama/Llama-3.2-1B-Instruct", 
            messages=messages, 
            temperature=0.1,
            max_tokens=512,
            top_p=0.5,
            stream=True
        )

        full_response = ""

        
        # Iterar sobre cada chunk, acumulando o conteúdo
        for chunk in stream:
            full_response += chunk.choices[0].delta.content  # ou "text", dependendo da estrutura do chunk

        # Imprimir toda a resposta junta
        return full_response


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
       
        if total_tokens + count <= 1000:
            limited_context.append(text)
            total_tokens += count
        else:
            break  
        
    print("Número total de tokens após limitação:", total_tokens)
    return limited_context
