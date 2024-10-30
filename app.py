from flask import Flask, request, render_template
# from haystack_components.pipeline import answer_question

app = Flask(__name__)

# Create a list to hold the messages
messages = []


# Define a route to handle the main page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the message from the form and add it to the list of messages
        message = request.form['message']
        if message:
            messages.append(('sender', message))
            # Call the model function to get the response

            # response = answer_question(message)
            response = "Boas pessoal"

            messages.append(('receiver', response))

    # Render the template with the messages
    return render_template('index.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=False, threaded=False)
