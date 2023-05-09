class FullStateRequests:
    def __init__(self,
                 full_state_list = ["GET_PROGRESS", "GET_EXERCISE", "GET_MEALS", "UPDATE_PARAMETERS", "GET_STATS", "KCALS_BURNED", "KCALS_GAINED"]) -> None:
        '''
            The constructor of the FullStateRequest.
                :param full_state_list: list, default = ["GET_PROGRESS", "GET_EXERCISE", "GET_MEALS", "UPDATE_PARAMETERS", "GET_STATS", "KCALS_BURNED", "KCALS_GAINED"]
                    The list of the FSM states that requires sending a request to the Business Logic
                    to create the response.
        '''
        self.full_state_list = full_state_list

    def get_update_params_request_prep(self, text : str, ners : dict) -> dict:
        '''
            This function creates the request payload for the update_params request.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        request_payload = {}

        # Finding the pairs of NOUNS and CARDINAL VALUES.
        for i in range(len(ners["NOUNS"])):
            min_dist = len(text)
            min_index = -1
            # Finding the nearest CARDINAL value for every NOUN.
            for j in range(len(ners["CARDINAL"])):
                temp_dist = text.index(str(ners["CARDINAL"][j])) - text.index(str(ners["NOUNS"][i]))
                if temp_dist < min_dist and temp_dist > 0:
                    min_dist = temp_dist
                    min_index = j
            # Updating the request payload.
            request_payload[ners["NOUNS"][i]] = ners["CARDINAL"][min_index]
        return request_payload

    def get_exercise_request_prep(self, text : str, ners : dict) -> dict:
        '''
            This function creates the request payload for the get_exercise request.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        return {
            "dates" : ners["DATE"]
        }

    def get_meals_request_prep(self, text : str, ners : dict) -> dict:
        '''
            This function creates the request payload for the get_meals request.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        return {
            "dates" : ners["DATE"]
        }

    def get_stats_prep(self, text : str, ners : dict) -> dict:
        '''
            This function creates the request payload for the get_stats request.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        return {
            "params" : ners["NOUNS"]
        }

    def get_kcals(self, text : str, ners : dict) -> dict:
        '''
            This function creates the request payload for the get_kcals request.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        return {
            "dates" : ners["DATE"]
        }

    def get_params_for_request(self, state : str, text : str, ners : dict) -> dict:
        '''
            This function returns the request payload for the state of the FSM.
                :param state: str
                    The state of the conversation on the FSM.
                :param text: str
                    The message sent to the chatbot.
                :param ners: dict
                    The named entities extracted from the message.
        '''
        # Checking the object is responsible for the state provided.
        if state not in self.full_state_list:
            raise ValueError(f"{state} is'n recognized as a functional state!")
        else:
            # If it is responsible, then depending on the state the suitable function is called.
            if state == "GET_PROGRESS" or state == "KCALS_BURNED" or state == "KCALS_GAINED":
                return {}
            elif state == "GET_EXERCISE":
                return self.get_exercise_request_prep(text, ners)
            elif state == "GET_MEALS":
                return self.get_meals_request_prep(text, ners)
            elif state == "UPDATE_PARAMETERS":
                return self.get_update_params_request_prep(text, ners)
            elif state == "GET_STATS":
                return self.get_stats_prep(text, ners)