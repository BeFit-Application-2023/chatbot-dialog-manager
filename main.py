# Importing the external libraries.
from flask import Flask, request, jsonify
from flask_script import Manager
from flask_migrate import Migrate
import threading
import requests
import random
import json
import time
import uuid

# Importing all needed modules.
from models import UserModel, MessageModel
from cache_round_robin import CacheRoundRobin
from transaction_saga import TransactionSaga
from dialog import DialogManager, PhraseFormatter, RandomPhrase, FullStateRequests
from cerber import SecurityManager
from schemas import MessageSchema
from config import ConfigManager
from models import db
from fsm import FSM

# Loading the configuration from the configuration file.
config = ConfigManager("config.ini")

# Creation of the message schema object.
message_schema = MessageSchema()

# Setting up the sqlalchemy database uri.
sqlalchemy_database_uri = f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}/{config.database.db_name}"

# Setting up the Flask dependencies.
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_DATABASE_URI"] = sqlalchemy_database_uri
app.secret_key = config.security.secret_key

migrate = Migrate(app, db)

# Creating the security manager for the service discovery.
service_discovery_security_manager = SecurityManager(config.service_discovery.secret_key)

# Computing the HMAC for Service Discovery registration.
SERVICE_DISCOVERY_HMAC = service_discovery_security_manager._SecurityManager__encode_hmac(
    config.generate_info_for_service_discovery()
)

# Creation of the Security Manager.
security_manager = SecurityManager(config.security.secret_key)

# Defining the empty services credentials holders.
DATA_WAREHOUSE_DATA = {}
services = {}
CACHE_SERVICES = {}
TELEGRAM_INTERFACE_DATA = {}

def send_heartbeats():
    '''
        This function sends heartbeat requests to the service discovery.
    '''
    # Getting the Service discovery hmac for message.
    service_discovery_hmac = service_discovery_security_manager._SecurityManager__encode_hmac({"status_code" : 200})
    while True:
        # Senting the request.
        response = requests.post(
            f"http://{config.service_discovery.host}:{config.service_discovery.port}/heartbeat/{config.general.name}",
            json = {"status_code" : 200},
            headers = {"Token" : service_discovery_hmac}
        )
        # Making a pause of 30 seconds before sending the next request.
        time.sleep(30)

# Registering to the Service discovery.
while True:
    # Sending the request to the service discovery.
    resp = requests.post(
        f"http://{config.service_discovery.host}:{config.service_discovery.port}/{config.service_discovery.register_endpoint}",
        json = config.generate_info_for_service_discovery(),
        headers={"Token" : SERVICE_DISCOVERY_HMAC}
    )

    # If the request is successful then we are going to request the credentials of the needed services.
    if resp.status_code == 200:
        while True:
            time.sleep(3)
            # Computing the Service Discovery HMAC for getting services credentials.
            service_discovery_hmac = SecurityManager(config.service_discovery.secret_key)._SecurityManager__encode_hmac(
                {"service_names" : ["cache-service-1", "cache-service-2", "data-warehouse-service", "intent-sidecar-service",
                                    "named-entity-recognition-sidecar-service", "sentiment-sidecar-service", "telegram_interface"]}
            )
            # Trying to get the credentials of the services from the Service Discovery.
            res = requests.get(
                f"http://{config.service_discovery.host}:{config.service_discovery.port}/get_services",
                json = {"service_names" : ["cache-service-1", "cache-service-2", "data-warehouse-service", "intent-sidecar-service",
                                           "named-entity-recognition-sidecar-service", "sentiment-sidecar-service", "telegram_interface"]},
                headers={"Token" : service_discovery_hmac}
            )
            # Checking is the request was successful.
            if res.status_code == 200:
                time.sleep(5)
                # Starting sending heartbeats.
                threading.Thread(target=send_heartbeats).start()

                # Splitting the requested data by services.
                res_json = res.json()
                CACHE_SERVICES = {service_info : res_json[service_info] for service_info in res_json
                                  if service_info in ["cache-service-1", "cache-service-2"]}

                DATA_WAREHOUSE_DATA = {
                    "host" : res_json["data-warehouse-service"]["general"]["host"],
                    "port" : res_json["data-warehouse-service"]["general"]["port"],
                    "security_manager" : SecurityManager(res_json["data-warehouse-service"]["security"]["secret_key"])
                }

                services = {service_info : res_json[service_info] for service_info in res_json
                            if service_info in ["intent-sidecar-service", "named-entity-recognition-sidecar-service", "sentiment-sidecar-service"]}

                TELEGRAM_INTERFACE_DATA = {
                    "host" : res_json["telegram_interface"]["general"]["host"],
                    "port" : res_json["telegram_interface"]["general"]["port"],
                    "security_manager" : SecurityManager(res_json["telegram_interface"]["security"]["secret_key"])
                }

                break
        break
    else:
        time.sleep(10)

function_to_service_mapping = {
    "sentiment" : "sentiment-sidecar-service",
    "intent" : "intent-sidecar-service",
    "ner" : "named-entity-recognition-sidecar-service"
}

service_to_function_mapping = {
    "sentiment-sidecar-service" : "sentiment",
    "intent-sidecar-service" : "intent",
    "named-entity-recognition-sidecar-service" : "ner"
}

# Creation of the cache round robin.
cache_manager = CacheRoundRobin(CACHE_SERVICES)

# Creation of the dialog Manager.
dialog_manager = DialogManager(FSM)

# Loading the predefined phrases and phrase formatter.
phrase_formats = json.load(open("phrases_formats.json", "r"))
predefined_phrases = json.load(open("predefined_phrases.json", "r"))

# Creation of the response generators.
phrase_formatter = PhraseFormatter(phrase_formats)
predefined_phrases_generator = RandomPhrase(predefined_phrases)
full_state_request_creator = FullStateRequests()

# Creation of the tables in the database.
with app.app_context():
    db.init_app(app)
    db.create_all()
    db.session.commit()

@app.route("/message", methods=["POST"])
def message():
    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        result, status_code = message_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            # Check if user is a registered one.
            telegram_user_id = result["telegram_user_id"]
            chat_id = result["chat_id"]

            # Getting the user record from the Data Base.
            user = UserModel.query.filter_by(telegram_id = telegram_user_id).first()

            # Announcing that the user is not registered.
            if not user:
                requests.post(
                    f"http://{TELEGRAM_HOST}:{TELEGRAM_PORT}/send_response",
                    json = {"text" : "Sorry you are not a registered user!",
                            "chat_id" : chat_id},
                    headers = {"Token" : None}
                )
                return {
                    "message" : "Not registered user!"
                }, 403
            else:
                # Getting the user id.
                user_id = user.id

            text = result["text"]
            date = time.time()
            correlation_id = str(uuid.uuid4())

            # Check message in cache.
            ner = cache_manager.get_value(text, "ner")
            sentiment = cache_manager.get_value(text, "sentiment")
            intent = cache_manager.get_value(text, "intent")

            grouped_results = {
                "ner" : ner,
                "sentiment" : sentiment,
                "intent" : intent
            }

            services_for_transaction_saga = []
            cached_values = {}
            is_cached_dict = {}

            # Selecting the services to access during the transaction saga.
            for result in grouped_results:
                if grouped_results[result] is not None:
                    cached_values[result] = grouped_results[result]
                    is_cached_dict[result] = True
                else:
                    services_for_transaction_saga.append(function_to_service_mapping[result])
                    is_cached_dict[result] = False

            selected_services_for_transaction = {service : services[service] for service in services_for_transaction_saga}

            # Running the transaction saga.
            transaction_saga_results = TransactionSaga(selected_services_for_transaction).start(
                {
                    "text" : text,
                    "correlation_id" : correlation_id
                }
            )

            # Adding the cached value to the transaction results.
            if len(cached_values) > 0:
                for cached_key in cached_values:
                    transaction_saga_results[cached_key] = cached_values[cached_key]

            # Replacing the services names to the use case provided by them.
            for key in transaction_saga_results:
                if key in service_to_function_mapping:
                    transaction_saga_results[service_to_function_mapping[key]] = transaction_saga_results[key]
                    del transaction_saga_results[key]

            intent = transaction_saga_results["intent"]
            ner = transaction_saga_results["ner"]
            sentiment = transaction_saga_results["sentiment"]

            print(f"Intent - {intent}")
            print(f"NER - {ner}")
            print(f"sentiment - {sentiment}")

            # Getting the last message sent by the user.
            message = MessageModel.query.filter_by(user_id = user_id).order_by(MessageModel.date.desc()).first()

            # Getting the last state of the conversation.
            last_state = message.state if message else "ANY"
            print(f"Last state - {last_state}")

            # Getting the new state of the dialog.
            new_state, ner = dialog_manager.get_new_state(last_state, intent, ner, sentiment)
            print(f"New state - {new_state}")

            # Setting up some metrics for the fact table.
            is_seq2seq = False
            business_logic_response = None
            is_cached_dict["sequence"] = False

            # Checking to which category the new state is part of.
            if new_state in full_state_request_creator.full_state_list:
                # Getting the parameters for the Business Logic request.
                params = full_state_request_creator.get_params_for_request(new_state, text, ner)

                # Making the call to the Business Logice service.
                business_logic_response = {}
                # TODO: Make request to business logic.

                # Getting the response.
                response = "Response from business logic."
            elif new_state in predefined_phrases_generator.servable_states:
                # Getting the predefined phrase for the state.
                response = predefined_phrases_generator.get_phrase(new_state)
            elif new_state == "SEQUENCE2SEQUENCE":
                # Getting the response from the NLG Service.
                response = "Message from seq2seq"
                is_seq2seq = True

            # Adding the new message to the Data Base.
            new_message = MessageModel(
                correlation_id,
                text,
                intent,
                sentiment,
                ner,
                response,
                is_seq2seq,
                business_logic_response,
                date,
                user_id,
                new_state
            )

            db.session.add(new_message)
            db.session.commit()

            # Creation of the request payload to the Data Warehouse.
            data_for_data_warehouse = {
                "time" : time.time(),
                "correlation_id" : correlation_id,
                "text" : text,
                "intent" : intent,
                "sentiment" : sentiment,
                "ner" : ner,
                "response" : response,
                "is_seq2seq" : is_seq2seq,
                "business_logic_response" : business_logic_response,
                "is_intent_cached" : is_cached_dict["intent"],
                "is_sentiment_cached" : is_cached_dict["sentiment"],
                "is_ner_cached" : is_cached_dict["ner"],
                "is_sequence_cached" : is_cached_dict["sequence"],
                "telegram_user_id" : telegram_user_id
            }

            # Computing the HMAC for the Data Warehouse.
            new_message_data_warehouse_hmac = DATA_WAREHOUSE_DATA["security_manager"]._SecurityManager__encode_hmac(data_for_data_warehouse)

            # Making the request to the Data Warehouse.
            data_warehouse_response = requests.post(
                f"http://{DATA_WAREHOUSE_DATA['host']}:{DATA_WAREHOUSE_DATA['port']}/message",
                json = data_for_data_warehouse,
                headers = {"Token" : new_message_data_warehouse_hmac}
            )
            print(data_warehouse_response.json())

            # Sending the chosen response to the Telegram Interface.
            telegram_interface_hmac = TELEGRAM_INTERFACE_DATA["security_manager"]._SecurityManager__encode_hmac({"text" : response, "chat_id" : chat_id})
            telegram_response = requests.post(
                f"http://{TELEGRAM_INTERFACE_DATA['host']}:{TELEGRAM_INTERFACE_DATA['port']}/send_response",
                json = {"text" : response, "chat_id" : chat_id},
                headers = {"Token" : telegram_interface_hmac}
            )

            return {
                "text" : response,
                "chat_id" : chat_id
            }, 200

@app.route("/user", methods=["POST"])
def user():
    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        status_code = 200

        result, status_code = message_schema.validate_json(request.json)
        if status_code != 200:
            # If the request body didn't passed the json validation a error is returned.
            return result, status_code
        else:
            # Extracting the code from the message.
            code = result["text"]
            # TODO: MAKE A REQUEST TO THE BUSINESS LOGIC TO REQUEST THE CODE OF THE USER.
            app_id = random.randint(1, 200)

            # Generation of the id for the new user.
            user_id = str(uuid.uuid4())

            # Adding the user to the data base.
            new_user = UserModel(
                user_id,
                result["telegram_user_id"],
                result["chat_id"],
                result["first_name"],
                result["last_name"],
                result["username"],
                app_id
            )

            db.session.add(new_user)
            db.session.commit()

            # Creation of the request payload for the Data Warehouse.
            data_for_data_warehouse = {
                "user_id" : user_id,
                "telegram_user_id" : result["telegram_user_id"],
                "chat_id" : result["chat_id"],
                "first_name" : result["first_name"],
                "last_name" : result["last_name"],
                "telegram_username" : result["username"],
                "app_id" : app_id
            }

            # Computing the HMAC for the request to the Data Warehouse.
            new_user_data_warehouse_hmac = DATA_WAREHOUSE_DATA["security_manager"]._SecurityManager__encode_hmac(data_for_data_warehouse)

            # Making the request to the Data Warehouse.
            data_warehouse_response = requests.post(
                f"http://{DATA_WAREHOUSE_DATA['host']}:{DATA_WAREHOUSE_DATA['port']}/user",
                json = data_for_data_warehouse,
                headers = {"Token" : new_user_data_warehouse_hmac}
            )
            print(data_warehouse_response.json())

            # Computing the HMAC for the Telegram Interface request.
            telegram_interface_hmac = TELEGRAM_INTERFACE_DATA["security_manager"]._SecurityManager__encode_hmac({"text" : "Hi, nice to meet you!", "chat_id" : result["chat_id"]})

            # Sending the Welcoming message to the telegram interface.
            telegram_response = requests.post(
                f"http://{TELEGRAM_INTERFACE_DATA['host']}:{TELEGRAM_INTERFACE_DATA['port']}/send_response",
                json = {"text" : "Hi, nice to meet you!", "chat_id" : result["chat_id"]},
                headers = {"Token" : telegram_interface_hmac}
            )

            return {
                "message" : "OK!"
            }, 200

# Running the application.
app.run(
    port = config.general.port,
    host = config.general.host
)