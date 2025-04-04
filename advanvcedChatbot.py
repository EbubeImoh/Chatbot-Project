import os
import json
import random
import nltk
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import speech_recognition as sr
import pyttsx3 
from transformers import pipeline
import requests
import sqlite3

# UNCOMMENT THIS BUT CCOMMENT IT BACK ONCE YOU'VE RUN THE ENTIRE CODE TO AVOID DOWNLOADING THE RESOURCES MORE THAN ONCE
# Ensure NLTK resources are available
# nltk.download('punkt')
# nltk.download('wordnet')
# nltk.download('averaged_perceptron_tagger')
# nltk.download('maxent_ne_chunker')
# nltk.download('words')

class ChatbotModel(nn.Module):
    def __init__(self, input_size, output_size):
        super(ChatbotModel, self).__init__()
        self.fc1 = nn.Linear(input_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, output_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x

class AdvancedChatbot:
    def __init__(self, intents_path, db_path='chatbot.db'):
        self.model = None
        self.intents_path = intents_path
        self.vocabulary = []
        self.intents = []
        self.responses = {}
        self.recognizer = sr.Recognizer()
        self.tts_engine = pyttsx3.init()
        self.db_path = db_path
        self.setup_database()
        self.load_intents()
        
        from transformers import pipeline
        self.qa_pipeline = pipeline(
            "question-answering", 
            model="distilbert-base-cased-distilled-squad", 
            tokenizer="distilbert-base-cased-distilled-squad"
        )
        

    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY, user TEXT, message TEXT, response TEXT)''')
        conn.commit()
        conn.close()

    def save_to_db(self, user, message, response):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO conversations (user, message, response) VALUES (?, ?, ?)", (user, message, response))
        conn.commit()
        conn.close()

    def load_intents(self):
        with open(self.intents_path, 'r') as f:
            intents_data = json.load(f)
        for intent in intents_data['intents']:
            self.intents.append(intent['tag'])
            self.responses[intent['tag']] = intent['responses']

    def recognize_speech(self):
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.recognizer.listen(source)
            try:
                return self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                return "Sorry, I couldn't understand that."
            except sr.RequestError:
                return "Speech service is unavailable."

    def speak(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def web_lookup(self, query):
        response = requests.get(f'https://api.duckduckgo.com/?q={query}&format=json')
        return response.json().get('Abstract', "No information found.")

    def named_entity_recognition(self, text):
        words = nltk.word_tokenize(text)
        pos_tags = nltk.pos_tag(words)
        named_entities = nltk.ne_chunk(pos_tags, binary=True)
        return [" ".join(c[0] for c in chunk) for chunk in named_entities if hasattr(chunk, 'label')]

    def chat(self, message, user="User"):
        entities = self.named_entity_recognition(message)
        response = ""
        
        if "stocks" in message:
            response = "Here are some trending stocks: AAPL, TSLA, GOOGL."
        elif "weather" in message:
            response = self.web_lookup(f"weather in {entities[0]}" if entities else "current weather")
        else:
            response = self.qa_pipeline(question=message, context="".join(self.responses.get("greeting", [""])))['answer']
        
        self.save_to_db(user, message, response)
        self.speak(response)
        return response

if __name__ == "__main__":
    assistant = AdvancedChatbot('intents.json')
    while True:
        message = assistant.recognize_speech()
        if message.lower() == 'exit':
            break
        print("User:", message)
        print("Chatbot:", assistant.chat(message))