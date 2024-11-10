from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from pymongo.errors import ConnectionFailure
import logging
from typing import List, Optional
import bcrypt
from utils.index import generate_jwt_token, env
from models.index import predict, chat, getChats, deleteChats, search_hotels, addToFavHotels, getFavHotels, deleteFavHotels, recommendation, saveUser, send_email
from dotenv import load_dotenv
import json
from typing import TypeVar, Protocol, Generic, runtime_checkable

load_dotenv()

app = FastAPI()
app = FastAPI(swagger_ui_parameters={"syntaxHighlight": False}) #Enable Swagger UI
# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up CORS (Cross-Origin Resource Sharing) to allow requests from all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow requests from all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # allow these HTTP methods
    allow_headers=["*"],  # allow all headers
)

#=============================================== DB Configurations =========================================
# MongoDB Atlas connection string
MONGODB_URI = env('MONGODB_URI') + '=true&w=majority&appName=Cluster0'

# Connect to MongoDB Atlas
try:
    client = MongoClient(MONGODB_URI)
    # Test if the connection is successful
    client.admin.command('ismaster')
    logging.info("MongoDB connection successful")
except ConnectionFailure as e:
    logging.error("MongoDB connection failed: %s", e)
    raise e


# Select database and collection
db = client["research-paramee"]
users_collection = db["users"]
admins_collection = db["admins"]
transactions_collection = db["transactions"]
favs_collection = db["fav"]
chats_collection = db["chats"]

# Define a Pydantic model for the user data
class User(BaseModel):
    email: str
    id: str
    given_name: str
    family_name: str
    picture: str
    verified_email: bool

#============================================================================================================

@app.get("/")
async def read_root():
    return {"message": "Hello, Welcome to our server !!!"}

# Registration route
@app.post("/register/")
async def register(user: User):
        # Check if the username already exists
        existing_user = users_collection.find_one({"email": user.email})

        if existing_user:
            logging.info(f"Username {user.email} already exists")
        else:  
        # Insert the new user into the database                                                                                 
            user_data = {"email": user.email, "id": user.id,  "given_name": user.given_name,
                "family_name": user.family_name,
                "picture": user.picture, "verified_email": user.verified_email}
            saveUser(user_data, db)
            logging.info(f"User {user.email} registered successfully with ID")
        return True        

# Define a Pydantic model for the admin login request
class LoginRequest(BaseModel):
    email: str
    password: str

# Login route
@app.post("/admin-login/")
async def login(login_request: LoginRequest):
        # Find the user in the database
        admin = admins_collection.find_one({"email": login_request.email})
        print(admin)
        if admin:
            admin['_id'] = str(admin['_id'])
            if not (login_request.password == admin["password"]):
                raise HTTPException(status_code=401, detail="Invalid email or password")
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # If the username and password are correct, return a success message 
        return {"message": "Login successful", "admin": admin}

# get users route
@app.get("/get-users/")
async def get_users():
    # Fetch all users
    users = users_collection.find().sort({ "_id": -1 })
    # Convert cursor to list of dictionaries and make it JSON serializable
    users_list = []
    for user in users:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
        users_list.append(user)
    return {"users": users_list}


class Query(BaseModel):
    name: str

# Prediction route
@app.post("/predict/")
async def prediction(query: Query):
    return predict(query.name)

class Chat(BaseModel):
     userId: str
     userName: str
     text: str

# Chat route
@app.post("/chat/")
async def chatBot(msg: Chat):
    return chat(msg, db)

class Recommendation(BaseModel):
     text: str
     userName: str
 
# Recommendation route
@app.post("/recommendation/")
async def recomm(msg: Recommendation):
    return recommendation(msg, db)

# Chat route
@app.get("/chat/{userId}")
async def getChatsByUserId(userId):
    return getChats(userId, db)

# Chat route
@app.delete("/chat/{userId}")
async def deleteChatsByUserId(userId):
    return deleteChats(userId, db)

class Fav(BaseModel):
     hotel: str
# Fav route
@app.post("/add-to-fav/{userId}")
async def addToFav(payload: Fav, userId, request: Request):
    hotel_data = json.loads(payload.hotel)
    return addToFavHotels(hotel_data, userId, db)

@app.get("/get-fav/{userId}")
async def getFav(userId):
    return getFavHotels(userId, db)

@app.delete("/delete-fav/{favId}")
async def deleteFav(favId):
    return deleteFavHotels(favId, db)

@app.get("/hotels/searchByCoordinates")
async def search_hotels_by_coordinates(
    latitude: float,
    longitude: float,
    arrival_date: str,
    departure_date: str,
    adults: int,
    children_age: str,
    room_qty: int,
    units: str,
    page_number: int,
    temperature_unit: str,
    languagecode: str,
    currency_code: str
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "arrival_date": arrival_date,
        "departure_date": departure_date,
        "adults": adults,
        "children_age": children_age,
        "room_qty": room_qty,
        "units": units,
        "page_number": page_number,
        "temperature_unit": temperature_unit,
        "languagecode": languagecode,
        "currency_code": currency_code
    }
    
    headers = {
        "X-RapidAPI-Key": env('RAPIDAPI_KEY'),
        "X-RapidAPI-Host": "booking-com15.p.rapidapi.com"
    }
    
    return search_hotels(params, headers)

class Model(BaseModel):
    """A base model that allows protocols to be used for fields."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
class PriceBreakdownItem:
    def __init__(self, name, details, item_amount):
        self.name = name
        self.details = details
        self.item_amount = item_amount

    def to_dict(self):
        return {
            "name": self.name,
            "details": self.details,
            "item_amount": self.item_amount
        }

@runtime_checkable
class CompositePriceBreakdown(Protocol):
    class Config:
        arbitrary_types_allowed = True
    def __init__(self, gross_amount, discounted_amount, currency, items: List[PriceBreakdownItem]):
        self.gross_amount = gross_amount
        self.discounted_amount = discounted_amount
        self.currency = currency
        self.items = items

    @classmethod
    def from_dict(cls, data):
        items = [PriceBreakdownItem(**item) for item in data['items']]
        return cls(
            gross_amount=data['gross_amount'],
            discounted_amount=data['discounted_amount'],
            currency=data['currency'],
            items=items
        )
        
    def to_dict(self, noOfDays):
        return {
            "gross_amount": self.gross_amount * noOfDays,
            "discounted_amount": self.discounted_amount,
            "currency": self.currency,
            "items": [item.to_dict() for item in self.items]  # Convert each PriceBreakdownItem to a dict
        }

class EmailTemplateSchema(BaseModel):
    customer_name: str
    hotel_name: str
    city_in_trans: str
    checkin_from: str
    checkin_until: str
    checkout_from: str
    checkout_until: str
    total_amount: float
    currencycode: str
    discounts_applied: Optional[float]
    composite_price_breakdown: CompositePriceBreakdown
    customer_email: EmailStr
    bookedDate: str
    bookedTime: str
    noOfDays: int
    
    class Config: arbitrary_types_allowed = True
    # Validator for composite_price_breakdown
    @field_validator('composite_price_breakdown', mode='before')
    def validate_composite_price_breakdown(cls, value):
        if isinstance(value, dict):
            return CompositePriceBreakdown.from_dict(value)
        elif isinstance(value, CompositePriceBreakdown):
            return value
        raise ValueError("Invalid format for composite_price_breakdown")
    
@app.post("/sendEmail")
async def sendEmail(schema: EmailTemplateSchema):
    # Ensure that composite_price_breakdown is correctly formatted as a CompositePriceBreakdown instance
    schema.composite_price_breakdown = CompositePriceBreakdown.from_dict(schema.composite_price_breakdown) \
        if isinstance(schema.composite_price_breakdown, dict) else schema.composite_price_breakdown
    return send_email(schema, db)

# get transactions
@app.get("/get-transactions/")
async def get_transactions():
    # Fetch all transactions
    transactions = transactions_collection.find().sort({ "_id": -1 })
    # Convert cursor to list of dictionaries and make it JSON serializable
    transactions_list = []
    for transaction in transactions:
        transaction["_id"] = str(transaction["_id"])  # Convert ObjectId to string
        transactions_list.append(transaction)
    return {"transactions": transactions_list}

# get favourites
@app.get("/get-favs/")
async def get_favs():
    # Fetch all favs
    favs = favs_collection.find().sort({ "_id": -1 })
    # Convert cursor to list of dictionaries and make it JSON serializable
    favs_list = []
    for fav in favs:
        fav["_id"] = str(fav["_id"])  # Convert ObjectId to string
        favs_list.append(fav)
    return {"favs": favs_list}

# get chats
@app.get("/get-chats/")
async def get_chats():
    # Fetch all chats
    chats = chats_collection.find().sort({ "_id": -1 })
    # Convert cursor to list of dictionaries and make it JSON serializable
    chats_list = []
    for chat in chats:
        chat["_id"] = str(chat["_id"])  # Convert ObjectId to string
        chats_list.append(chat)
    return {"chats": chats_list}