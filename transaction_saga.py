# Importing all needed modules
import requests
import threading
from cerber import SecurityManager


class TransactionSaga:
    def __init__(self, services : dict) -> None:
        '''
            The constructor of the Transaction Saga.
                :param services: dict
                    The dictionary containing the service credentials.
        '''
        self.services = services
        self.security_managers = {
            service : SecurityManager(services[service]["security"]["secret_key"])
            for service in services
        }
        self.condition = threading.Condition()
        self.response_gatherer = {}
        self.response_gatherer_lock = threading.Lock()

    def request_service(self, service_name : str, json : dict) -> None:
        '''
            This function send the request to the required service concurrently.
                :param service_name: str
                    The name of the service.
                :param json: dict
                    The request payload.
        '''
        # Computing the HMAC for the request to the service.
        hmac = self.security_managers[service_name]._SecurityManager__encode_hmac(json)

        # Making the request to the service.
        response = requests.post(
            f"http://{self.services[service_name]['general']['host']}:{self.services[service_name]['general']['port']}/serve",
            json = json,
            headers = {"Token" : hmac}
        )

        # Acquiring the response gatherer lock.
        self.response_gatherer_lock.acquire()
        if response.status_code == 200:
            # Adding the response to the response gatherer.
            self.response_gatherer[service_name] = response.json()["prediction"]
        else:
            # Adding None if the response failed.
            self.response_gatherer[service_name] = None
        # Checking if all services responded.
        if len(self.response_gatherer) == len(self.services):
            with self.condition:
                # Notifying the condition that all responses where gathered.
                self.condition.notify()
        self.response_gatherer_lock.release()

    def start(self, json : dict) -> dict:
        '''
            This function runs the Transaction Saga and returns the results of the requests.
                :param json: dict
                    The request payload.
                :returns: dict
                    The results of the requests.
        '''
        # Starting the threads of requests.
        for service_name in self.services:
            threading.Thread(target=self.request_service, args=(service_name, json)).start()

        # Waiting for the requests to finish.
        with self.condition:
            self.condition.wait()

        return self.response_gatherer