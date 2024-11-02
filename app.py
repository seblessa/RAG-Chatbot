from flask import Flask, request, render_template, jsonify, stream_with_context, Response
from haystack_components.pipeline import answer_question, document_processor_pipeline
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
messages = []


@app.route('/', methods=['GET'])
def index():
    messages = []
    return render_template('index.html', messages=messages)


@app.route('/send_message', methods=['POST'])
def send_message():
    # Armazena a mensagem do usuário e responde imediatamente
    message = request.json.get('message', '')
    if message:
        messages.append(('sender', message))
        return jsonify({'status': 'received'})
    return jsonify({'status': 'error'}), 400


@app.route('/stream_response', methods=['POST'])
def stream_response():
    message = request.json.get('message', '')
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    answer = answer_question(message)['LLM']['response']
    messages.append(('receiver', answer))
    return answer


# Configuração para armazenamento temporário de ficheiros
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    file = request.files['file']
    print(file.filename)
    # Verificar se o ficheiro está presente e seguro para salvar
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty file name'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Executar a pipeline nos documentos
    try:
        print(filepath)
        result = document_processor_pipeline(filepath)

        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, threaded=False)
