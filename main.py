from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import spacy
import random

# Load English NLP model
nlp = spacy.load("en_core_web_sm")

app = FastAPI()

# Request model
class QuizRequest(BaseModel):
    paragraph: str
    quizType: str
    questionCount: int

# Constants
MIN_WORDS = 30
MAX_WORDS = 300
MAX_QUESTIONS = 10

def generate_mcq(doc, num_questions):
    questions = []
    keywords = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
    keywords = list(set(keywords))  # unique

    for i in range(min(num_questions, len(keywords))):
        answer = keywords[i]
        question_text = doc.text.replace(answer, "_____")
        distractors = random.sample([k for k in keywords if k != answer], k=min(3, len(keywords)-1))
        distractors.append(answer)
        random.shuffle(distractors)

        questions.append({
            "question": f"Fill in the blank: {question_text}",
            "options": distractors,
            "answer": answer
        })
    return questions

def generate_true_false(doc, num_questions):
    sentences = list(doc.sents)
    questions = []
    for i in range(min(num_questions, len(sentences))):
        sent = sentences[i].text
        if random.random() > 0.5:
            questions.append({"question": f"True or False: {sent}", "answer": "True"})
        else:
            words = sent.split()
            if len(words) > 3:
                words[random.randint(0, len(words)-1)] = "something"
            altered = " ".join(words)
            questions.append({"question": f"True or False: {altered}", "answer": "False"})
    return questions

def generate_fill_blank(doc, num_questions):
    sentences = list(doc.sents)
    questions = []
    for i in range(min(num_questions, len(sentences))):
        sent_words = sentences[i].text.split()
        if len(sent_words) > 4:
            blank_index = random.randint(0, len(sent_words)-1)
            answer = sent_words[blank_index]
            sent_words[blank_index] = "_____"
            questions.append({
                "question": " ".join(sent_words),
                "answer": answer
            })
    return questions

@app.post("/generate")
def generate_quiz(request: QuizRequest):
    # Word count check
    word_count = len(request.paragraph.split())
    if word_count < MIN_WORDS or word_count > MAX_WORDS:
        raise HTTPException(status_code=400, detail=f"Paragraph must be between {MIN_WORDS} and {MAX_WORDS} words.")

    # Limit questions
    question_count = min(request.questionCount, MAX_QUESTIONS)

    doc = nlp(request.paragraph)

    if request.quizType == "mcq":
        questions = generate_mcq(doc, question_count)
    elif request.quizType == "truefalse":
        questions = generate_true_false(doc, question_count)
    elif request.quizType == "fillblank":
        questions = generate_fill_blank(doc, question_count)
    else:
        raise HTTPException(status_code=400, detail="Invalid quiz type.")

    return {"questions": questions}
