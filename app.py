import os

from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from utils import generate_prompt
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

openai.api_key = openai.api_key = os.getenv("OPENAI_API_KEY")

def create_database():
    with app.app_context():
        db.create_all()
    print("SQLite database created.")

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
        
        print(parameters)

        response = openai.Completion.create( 
        model="text-davinci-003",
        prompt=generate_prompt(result),
        temperature=0.8,
        max_tokens=200
        )
        
        print(response)
        other=response.choices[0].text
        # other = other[1:] # will need to throw out the first of the response, as it is the "sure, allan! part"
        print(other)

        # this now returns the response from the model, which will be x nummber of question and answer pairs 
        # separated by the break string defined. Parse this response again, and save to the database 

        # will provide option for users to delete / change questions or answers 
        qa_pairs = other.split('\n\n')
        print(qa_pairs)
        qa_pairs = qa_pairs[1:]
        for qa_pair in qa_pairs:
            # for each qa_pair, split by => and, initiaize the db model 
            qa_pair = qa_pair.split('\n')
            #print(qa_pair)

            newPrompt = Prompt(question=qa_pair[0], answer=qa_pair[1]) 
            try:
                db.session.add(newPrompt)
                db.session.commit()
            except:
                return 'There was an issue adding your question and answers'
        return redirect('/')
    else:
        qa_pairs = Prompt.query.order_by(Prompt.id).all()
        return render_template(url_for('index.html', qa_pairs=qa_pairs))

@app.route('/delete/<int:id>')
def delete(id):
    item_to_delete = Prompt.query.get_or_404(id)

    try:
        db.session.delete(item_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was a problem deleting that task'

if __name__ == "__main__":
    # with app.app_context():
    #     create_database()
    app.run(debug=True)