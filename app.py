from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizGPT.db'
db = SQLAlchemy(app)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return '<Question Answer Pair %r>' % self.id
    
@app.route('/', methods=['POST', 'GET'])
def index():
    # Data Structures and Algorithms, 10, Medium 

    if request.method == 'POST':
        parameters = request.form['content']
        result = parameters.split(",")

        response = openai.Completion.create( 
        model="text-davinci-003",
        prompt=generate_prompt(result),
        temperature=0.6
        )

        response = response[1:] # will need to throw out the first of the response, as it is the "sure, allan! part"

        # this now returns the response from the model, which will be x nummber of question and answer pairs 
        # separated by the break string defined. Parse this response again, and save to the database 

        # will provide option for users to delete / change questions or answers 
        qa_pairs = response.split('!--this is a line break--!')
        for qa_pair in qa_pairs:
            # for each qa_pair, split by => and, initiaize the db model 
            qa_pair = qa_pair.split('=>')
            newPrompt = Prompt(question=qa_pair[0], answer=qa_pair[1]) 
            try:
                db.session.add(newPrompt)
                db.session.commit()
            except:
                return 'There was an issue adding your question and answers'
    else:
        qa_pairs = Prompt.query.order_by(Prompt.id).all()
        return render_template('index.html', qa_pairs=qa_pairs)


def generate_prompt(result):
    
    return 'Write me ' + result[1] + ' questions for the following: \n' + \
       'topic: ' + result[0] + '\n' + \
       'difficulty: ' + result[2] + '\n' + \
       'separate each of the questions and answers with the string "!--this is a line break--!" and in front of each' + \
       'question and answer, annotate them with => in front.'


