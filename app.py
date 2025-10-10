from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import spacy
import nltk
from nltk.corpus import wordnet

# ----------------------------
#  INITIAL SETUP
# ----------------------------

# Download NLTK data (only runs once)
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

# Initialize FastAPI
app = FastAPI(title="Smart Study Question Generator API")

# Allow frontend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
#  DATA MODEL
# ----------------------------

class QuizRequest(BaseModel):
    paragraph: str
    quizType: str
    questionCount: int


# ----------------------------
#  ENDPOINT
# ----------------------------

@app.post("/generate")
def generate_quiz(request: QuizRequest):
    """
    Generate study questions from input text.
    Supported quizType values: fillblank, truefalse, mcq
    """
    doc = nlp(request.paragraph)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    questions = []

    for i in range(min(request.questionCount, len(sentences))):
        sentence = sentences[i]
        question_data = {}

        # ----------------------------
        # FILL IN THE BLANK TYPE
        # ----------------------------
        if request.quizType.lower() == "fillblank":
            nouns = [token.text for token in nlp(sentence) if token.pos_ == "NOUN"]
            if nouns:
                word = random.choice(nouns)
                question = sentence.replace(word, "_____")
                question_data = {"question": question, "answer": word}
            else:
                question_data = {"question": sentence, "answer": None}

        # ----------------------------
        # TRUE / FALSE TYPE
        # ----------------------------
        elif request.quizType.lower() == "truefalse":
            words = sentence.split()
            if len(words) > 3:
                random_word = words[-1]
                altered = random_word[::-1]  # simple distortion
                false_sentence = " ".join(words[:-1] + [altered])
                question_data = {
                    "question": f"True or False: {false_sentence}",
                    "answer": "False",
                }
            else:
                question_data = {"question": f"True or False: {sentence}", "answer": "True"}

        # ----------------------------
        # MULTIPLE CHOICE TYPE
        # ----------------------------
        elif request.quizType.lower() == "mcq":
            nouns = [token.text for token in nlp(sentence) if token.pos_ == "NOUN"]
            if nouns:
                word = random.choice(nouns)
                question = sentence.replace(word, "_____")

                # Generate distractors using WordNet
                distractors = []
                synsets = wordnet.synsets(word)
                if synsets:
                    for lemma in synsets[0].lemmas()[:4]:
                        lemma_name = lemma.name().replace("_", " ")
                        if lemma_name.lower() != word.lower():
                            distractors.append(lemma_name)

                # Combine correct + distractors
                options = list(set([word] + distractors))
                random.shuffle(options)

                question_data = {
                    "question": question,
                    "options": options,
                    "answer": word,
                }
            else:
                question_data = {"question": sentence, "answer": None}

        # ----------------------------
        # DEFAULT CASE (if quizType invalid)
        # ----------------------------
        else:
            question_data = {"question": sentence, "answer": None}

        questions.append(question_data)

    return {"questions": questions}


# ----------------------------
#  ROOT TEST ROUTE
# ----------------------------
@app.get("/")
def home():
    return {"message": "Smart Study Question Generator API is running 🚀"}
