from fastapi import FastAPI
from pydantic import BaseModel
import random
import spacy
import nltk
from nltk.corpus import wordnet

# Download NLTK data (run once)
nltk.download("wordnet")
nltk.download("omw-1.4")

app = FastAPI()
nlp = spacy.load("en_core_web_sm")

# Input Schema
class QuizRequest(BaseModel):
    paragraph: str
    quizType: str
    questionCount: int

@app.post("/generate")
def generate_quiz(request: QuizRequest):
    doc = nlp(request.paragraph)
    sentences = [sent.text.strip() for sent in doc.sents]

    questions = []

    for i in range(min(request.questionCount, len(sentences))):
        sentence = sentences[i]
        question_data = {}

        if request.quizType == "fillblank":
            # Choose a noun to blank out
            nouns = [token.text for token in nlp(sentence) if token.pos_ == "NOUN"]
            if nouns:
                word = random.choice(nouns)
                question = sentence.replace(word, "_____")
                question_data = {"question": question, "answer": word}
            else:
                question_data = {"question": sentence, "answer": None}

        elif request.quizType == "truefalse":
            # True/False by altering a word
            words = sentence.split()
            if len(words) > 3:
                random_word = words[-1]
                altered = random_word[::-1]  # simple distortion
                false_sentence = " ".join(words[:-1] + [altered])
                question_data = {
                    "question": f"True or False: {false_sentence}",
                    "answer": "False"
                }
            else:
                question_data = {"question": f"True or False: {sentence}", "answer": "True"}

        elif request.quizType == "mcq":
            # Multiple choice: blank a word, provide distractors
            nouns = [token.text for token in nlp(sentence) if token.pos_ == "NOUN"]
            if nouns:
                word = random.choice(nouns)
                question = sentence.replace(word, "_____")

                # Generate distractors
                distractors = []
                synsets = wordnet.synsets(word)
                if synsets:
                    for lemma in synsets[0].lemmas()[:3]:
                        if lemma.name().lower() != word.lower():
                            distractors.append(lemma.name().replace("_", " "))

                options = list(set([word] + distractors))
                random.shuffle(options)

                question_data = {
                    "question": question,
                    "options": options,
                    "answer": word
                }
            else:
                question_data = {"question": sentence, "answer": None}

        questions.append(question_data)

    return {"questions": questions}
