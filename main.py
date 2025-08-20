from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import spacy
import random

# Load English NLP model
nlp = spacy.load("en_core_web_sm")

app = FastAPI()
