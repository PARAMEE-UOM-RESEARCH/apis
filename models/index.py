import google.generativeai as genai
from utils.index import env
import requests
from fastapi import HTTPException

#THIS IS BASED ON GOOGLE LLM's
def predict(query):
    try:
        def to_markdown(text):
            return text

        genai.configure(api_key=env("API_KEY"))

        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)

        model = genai.GenerativeModel(env('AI_MODEL'))

        response = model.generate_content(query)

        print(response.text)

        return to_markdown(response.text)
    except:
         raise HTTPException(status_code=500, detail="Internal Server Error")

def chat(prompt, db):
    try:
        chat_collection = db["chats"]
   
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        payload = {
            "prompt": {
            "text": f"My name is {prompt.userName}. I'm a micro Entrepreneur. You are my assistant. Please answer this question '{prompt.text}'. It's best to respond to my message. Try to act assistant and casual rather than being very formal."
            }
        }

        response = requests.post(env('CHAT_MODEL') + '=AIzaSyD4z63UDBeKGjktRqd_N_SOEmFifQhJCm4',json=payload)
        response = response.json()

        chat_data = {"userId": prompt.userId, "user": prompt.text,  "assistant": response["candidates"][0]["output"]}
        chat_collection.insert_one(chat_data)
        
        return response["candidates"][0]["output"]
    except:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def getChats(userId, db):
    try:
        chat_collection = db["chats"]
        chats = chat_collection.find({"userId": userId})
        chats = list(chats)
        for chat in chats:
            chat["_id"] = str(chat["_id"])
        return chats

    except:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def deleteChats(userId, db):
    try:
        chat_collection = db["chats"]
        chat_collection.delete_many({"userId": userId})
        return {"mesage": "Chats Deleted Successfully"}

    except:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
def search_hotels(params, headers): 
    try:
        response = requests.get(env("BOOKING_URL"), headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch hotels")
