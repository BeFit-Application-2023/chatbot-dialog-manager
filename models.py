# Importing all needed modules
from flask_sqlalchemy import SQLAlchemy

# Creating the SQLAlchemy client.
db = SQLAlchemy()

class UserModel(db.Model):
    # Defining the User table name.
    __tablename__ = "user"

    # Defining the column names.
    id = db.Column(db.String(64), primary_key=True)
    telegram_id = db.Column(db.Integer, unique=True)
    chat_id = db.Column(db.Integer, unique=True)
    first_name = db.Column(db.String(32), unique=False, nullable=True)
    last_name = db.Column(db.String(32), unique=False, nullable=True)
    telegram_username = db.Column(db.String(64), unique=True, nullable=True)
    app_id = db.Column(db.Integer, unique=True, nullable=False)

    def __init__(self, index, telegram_id, chat_id, first_name, last_name, telegram_username, app_id):
        self.id = index
        self.telegram_id = telegram_id
        self.chat_id = chat_id
        self.first_name = first_name
        self.last_name = last_name
        self.telegram_username = telegram_username
        self.app_id = app_id

    def __repr__(self):
        return f"<User telegram_id = {self.telegram_id}>"


class MessageModel(db.Model):
    # Setting up the table name.
    __tablename__ = 'messages'

    # Setting up the column names and data types.
    id = db.Column(db.String(64), primary_key=True)
    text = db.Column(db.Text, unique=False)
    intent = db.Column(db.String(64), unique=False)
    sentiment = db.Column(db.Float, unique=False)
    ner = db.Column(db.JSON, unique=False)
    response = db.Column(db.Text, unique=False)
    is_seq2seq = db.Column(db.Boolean, unique=False)
    business_logic_response = db.Column(db.JSON, unique=False, nullable=True)
    date = db.Column(db.Float, unique=False)
    user_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=True)
    state = db.Column(db.String(64), unique=False)

    def __init__(self, index, text, intent, sentiment, ner, response, is_seq2seq, business_logic_response, date, user_id, state="ANY"):
        self.id = index
        self.text = text
        self.intent = intent
        self.sentiment = sentiment
        self.ner = ner
        self.response = response
        self.is_seq2seq = is_seq2seq
        self.business_logic_response = business_logic_response
        self.date = date
        self.state = state
        self.user_id = user_id
