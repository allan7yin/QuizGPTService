def generate_prompt(result):
    return 'Generate a quiz of' + result[1] + 'questions of the difficulty' + result[2] + ' from the following prompt: ' + result[0] + '\n' + \
        'Also generate answers for each of the questions generated from the prompt. Let the formatting be "Question: ..." \
              then a new line, and then with its answer as "Answer: ..." for each of the questions. Each block of question and answer is separated with 2 new lines.'