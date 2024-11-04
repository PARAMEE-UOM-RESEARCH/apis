import google.generativeai as genai
from utils.index import env
import requests
from fastapi import HTTPException
import json
from bson import json_util, ObjectId
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr
from jinja2 import Template
import traceback
import datetime

load_dotenv()

def saveUser(profile, db):
    try:
        users_collection = db["users"]
        users_collection.insert_one(profile)
        return {"message": "Insert Successfully."}
    except:
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        
        genai.configure(api_key=os.environ["API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"My name is {prompt.userName}. I'm a traveller. You are my assistant. Please answer this question '{prompt.text}'. It's best to respond to my message. Try to act assistant and casual rather than being very formal.")

        chat_data = {"userId": prompt.userId, "user": prompt.text,  "assistant": response.text}
        chat_collection.insert_one(chat_data)
        
        return response.text
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
def recommendation(prompt, db):
    try:
   
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        genai.configure(api_key=os.environ["API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"My name is {prompt.userName}. I'm a traveller. You are my assistant. Please rate this hotel and give recommendations by analysing this object '{prompt.text}'. It's best to respond to my message. Try to act assistant and casual rather than being very formal.")
        
        return response.text
    except Exception as e:
        print(e)
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
    
def addToFavHotels(payload, userId, db): 
    try:
        fav_collection = db["fav"]
        # Ensure payload is directly used if it's already a dictionary
        fav_document = {
            "userId": userId,
            "hotel": payload
        }
        # Insert the document correctly
        fav_collection.insert_one(fav_document)
        return {"message": "Fav added successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to add to favorites")

def getFavHotels(userId, db):
    try:
        fav_collection = db["fav"]
        # Fetch documents from the collection
        cursor = fav_collection.find({"userId": userId})
        # Convert cursor to list
        fav_list = list(cursor)
        # Convert BSON to JSON serializable format
        return json.loads(json_util.dumps(fav_list))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch favorite hotels")
    
def deleteFavHotels(favId, db):
    try:
        fav_collection = db["fav"]
        object_id = ObjectId(favId)
        fav_collection.delete_one({"_id": object_id})
        return {"message": "Fav Hotel Deleted"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to delete favorite hotels")

def send_email(schema, db):
    try:
        sender_email = "codex.dev.m1@gmail.com"
        sender_password = "ijihiuyxreexlirh"
        subject= f'Booking Confirmation and Payment Receipt – {schema.hotel_name}'
        
        transaction_date = datetime.datetime.now().strftime("%Y/%m/%d")
        transaction_time = datetime.datetime.now().strftime("%H:%M")
        
        with open("email-templates/payment-receipt.html", "r") as file:
            template = Template(file.read())
            html_content = template.render(
                                            subject=subject,
                                            customer_name=schema.customer_name,
                                            hotel_name=schema.hotel_name,
                                            city_in_trans=schema.city_in_trans,
                                            checkin_from=schema.checkin_from,
                                            checkin_until=schema.checkin_until,
                                            checkout_from=schema.checkout_from,
                                            checkout_until=schema.checkout_until,
                                            total_amount=schema.total_amount,
                                            currencycode=schema.currencycode,
                                            composite_price_breakdown=schema.composite_price_breakdown.to_dict(schema.noOfDays),
                                            bookedDate=schema.bookedDate,
                                            bookedTime=schema.bookedTime,
                                            transaction_date= transaction_date,
                                            transaction_time= transaction_time,
                                            noOfDays=schema.noOfDays
                                        )

        transactions_collection = db["transactions"]
        transactions_collection.insert_one({
                                            "subject": subject,
                                            "customer_email": schema.customer_email,
                                            "customer_name": schema.customer_name,
                                            "hotel_name": schema.hotel_name,
                                            "city_in_trans": schema.city_in_trans,
                                            "checkin_from": schema.checkin_from,
                                            "checkin_until": schema.checkin_until,
                                            "checkout_from": schema.checkout_from,
                                            "checkout_until": schema.checkout_until,
                                            "total_amount": schema.total_amount,
                                            "currencycode": schema.currencycode,
                                            "composite_price_breakdown": schema.composite_price_breakdown.to_dict(schema.noOfDays),
                                            "transaction_date": transaction_date,
                                            "transaction_time": transaction_time,
                                            "bookedDate":schema.bookedDate,
                                            "bookedTime":schema.bookedTime,
                                            "noOfDays": schema.noOfDays
                                        })


        # Create the email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = schema.customer_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        # Send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, message["To"], message.as_string())

        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        # Print exception details
        print(f"An error occurred: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")