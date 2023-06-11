import json
import os
import threading

from flask import Flask, render_template, url_for, request, redirect
import pika
from utils import generate_prompt, MOCK_PROMPT
import openai

app = Flask(__name__)
env = os.environ["ENVIRONMENT"]

# RabbitMQ singleton channel
global global_rabbitmq_channel
global_rabbitmq_channel = None

# some configuration data we will keep here 
rabbitmq_user = os.environ["RABBITMQ_USER"]
rabbitmq_password = os.environ["RABBITMQ_PASSWORD"]
rabbitmq_host = os.environ["RABBITMQ_HOST"]
rabbitmq_port = int(os.environ["RABBITMQ_PORT"])

request_queue = os.environ.get("REQUEST_QUEUE")
response_queue = os.environ.get("RESPOSNE_QUEUE")

gpt_exchnage = os.getenv("GPT_EXCHANGE")

gpt_routing_key = os.getenv("GPT_TO_GATEWAY_ROUTING_KEY")

openai.api_key = os.getenv("OPENAI_API_KEY")

class QuestionDto:
    def __init__(self):
        self.questionId = None
        self.text = None
        self.options = []
        self.answers = []

class OptionDto:
    def __init__(self):
        self.optionId = None
        self.text = None

class AnswerDto:
    def __init__(self):
        self.answerId = None
        self.text = None


def parse_response(text, numOptions): # need numOptions to know how many to parse into
    questions = text.split("\n\n")
    quiz = []

# ['', 'Question 1: What is the result of 75 + 16?', 'A: 91', 'B: 81', 'C: 89', 'D: 71', 'Answer: A'], the first one has extra space in it, remeber 
    for question in questions:
        # for each question, parse and place into an object
        parsed_response = question.split("\n")

        entry = QuestionDto()
        if parsed_response[0] == '':
            parsed_response = parsed_response[1:]
        
        for index in range(len(parsed_response)):
            if index == 0:
                # question
                entry.text = parsed_response[index]
            elif index == len(parsed_response) - 1:
                # last one, this is the answer 
                entry.answers = [parsed_response[index]]
            else:
                # this means we are on an option 
                entry.options.append(parsed_response[index])
            
        quiz.append(entry)

    return quiz
    
@app.route('/')
def chatgpt_request(): #topic, numQuestions, numOptions, difficulty):
    if env == "dev":
        response = openai.Completion.create( 
        model="text-davinci-003",
        # prompt=generate_prompt(topic, numQuestions, numOptions, difficulty),
        prompt=MOCK_PROMPT,
        temperature=0.8,
        max_tokens=1000
        )

    print(response)
    return response

def callback(ch, method, properties, body): # called when message from queue has been consumed 
    try:
        message = json.loads(body) # get python object from the json 
        # this JSON will be in the format of CreateQuizRequestDto.java -> id, topic, num questions, number of options, difficulty. 
        print(message)
        quiz_id = message["id"]
        topic = message["topic"]
        numQuestions = message["numberOfQuestions"]
        numOptions = message["numberOfOptionsPerQuestion"]
        difficulty = message["difficulty"]

        generated_text = chatgpt_request(topic, numQuestions, numOptions, difficulty)
        if generated_text is None:
            print("Error generating text.")
            return
        text = generated_text["choices"][0]["text"]
        formatted_quiz_dto = parse_response(text, numOptions)

        # quizDto is what is being returned 
        quizDto = {
            "id": quiz_id,
            "questions": formatted_quiz_dto
        }

        json_data = json.dumps(quizDto)
        print("Reponse Message: " + json_data)

        ch.basic_publish(exchange=gpt_exchnage, routing_key=gpt_routing_key, body=json_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exception:
        print(exception)

def connect_to_rabbitmq_server():
    global global_rabbitmq_channel

    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, virtual_host=rabbitmq_user, credentials=credentials))
    print(f"Successfully connected to RabbitMQ at {rabbitmq_host}") if connection.is_open else print(f"Failed to connect to RabbitMQ at {rabbitmq_host}")

    # create a channel 
    global_rabbitmq_channel = connection.channel()
    # declare the queues (which have also been declared on the other end)
    global_rabbitmq_channel.queue_declare(queue=request_queue)
    global_rabbitmq_channel.queue_declare(queue=response_queue)    
    
def start_consuming():
    try:
        # establish connection to RabbitMQ channel, 
        global global_rabbitmq_channel
        connect_to_rabbitmq_server()
        if global_rabbitmq_channel is None:
            print("Error connecting to input queue. Exiting...")
            return "Error: Failed to connect to RabbitMQ"
        else:
            print("Successfully connected to RabbitMQ")
        
        global_rabbitmq_channel.basic_qos(prefetch_count=1) # indicates that the channel will only prefetch and process one message at a time before waiting for an acknowledgment.
        global_rabbitmq_channel.basic_consume(queue=request_queue, on_message_callback=callback) # callback function called when message is consumed 
        global_rabbitmq_channel.start_consuming()
    except Exception as exception:
        print(exception)


# complete this one time, first time app is started
@app.before_first_request
def startup():
    print('Starting RabbitMQ thread')
    rabbitmq_thread = threading.Thread(target=start_consuming)
    rabbitmq_thread.start()


if __name__ == "__main__":
    print('Starting Flask app. Environment: ', env)
    if env == "dev":
        print("In dev environment.")
        app.run(host="0.0.0.0", port=5000)
