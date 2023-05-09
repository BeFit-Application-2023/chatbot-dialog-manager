# Importing all needed modules.
import requests
from cerber import SecurityManager


class CacheRoundRobin:
    def __init__(self, caches : dict) -> None:
        '''
            The constructor of the Cache Round Robin.
                :param caches: dict
                    The dictionary representing the credentials of the caches.
        '''
        # Setting up the class fields.
        self.caches = caches
        self.caches_list = list(self.caches.keys())
        self.responsible_cache = self.caches_list[0]

        # Configuring the HMAC generators for the caches.
        self.security_managers = {
            cache : SecurityManager(caches[cache]["security"]["secret_key"])
            for cache in caches
        }

    def turn(self) -> None:
        '''
            This function changes the responsible cache.
        '''
        self.responsible_cache = [cache for cache in self.caches_list if cache != self.responsible_cache][0]

    def get_value(self, text : str, service : str) -> dict:
        '''
            This function calls the cache of the systems.
            If the call fails or the cache returns a None then another cache is used.
            Finally the responsible cache is changed.
                :param text: str
                    The text of the message.
                :param service: str
                    The name of the service to check the cache for.
        '''
        # Creation of the request body.
        data_json = {
            "text" : text,
            "service" : service
        }
        # Generation of the HMAC for the cache.
        hmac = self.security_managers[self.responsible_cache]._SecurityManager__encode_hmac(data_json)

        # Requesting the Cache.
        response = requests.get(
            f"http://{self.caches[self.responsible_cache]['general']['host']}:{self.caches[self.responsible_cache]['general']['port']}/cache",
            json = data_json,
            headers = {"Token" : hmac}
        )

        # Checking if the request was successful.
        if response.status_code == 200:
            # Turning the responsible cache and returning the result.
            self.turn()
            return response.json()["prediction"]
        else:
            # If the request to the first cache fails, then the second cache is tried.
            other_cache = [cache for cache in self.caches_list if cache != self.responsible_cache][0]

            # Generation of the HMAC for the cache.
            hmac = self.security_managers[other_cache]._SecurityManager__encode_hmac(data_json)

            # Requesting the Cache.
            response = requests.get(
                f"http://{self.caches[other_cache]['general']['host']}:{self.caches[other_cache]['general']['port']}/cache",
                json = data_json,
                headers = {"Token" : hmac}
            )

            # Turning the responsible cache and returning the result.
            self.turn()
            if response.status_code == 200:
                return response.json()["prediction"]
            else:
                return None