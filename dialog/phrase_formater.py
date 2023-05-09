class PhraseFormatter:
    def __init__(self, phrases_formats : dict) -> None:
        '''
            The constructor of the Phrase Formater.
                :param phrases_formats: dict
                    The mapper of the state to phrase formats list.
        '''
        self.phrases_formats = phrases_formats
        self.servable_intents = list(self.phrases_formats.keys())

    def __call__(self, state : str, response_json : dict) -> str:
        '''
            This function creates the chatbot response depending of the Business Logic response.
                :param state: str
                    The state of the dialog FSM.
                :param response_json: dict
                    The response dictionary of the Business Logic service.
        '''
        if state == "GET_PROGRESS":
            # Checking if the user has any set progress.
            if response_json["exists"] == "no-progress":
                return self.phrases_formats[state]["no-progress"]
            else:
                # Extraction of the values from the response and formatting the response.
                value = response_json["value"]
                measure_of_progress = response_json["measure_of_progress"]
                return self.phrases_formats[state]["exists"].format(value, measure_of_progress)
        elif state == "GET_EXERCISE":
            # Filling the response form with the response data.
            date = response_json["date"]
            exercise_list = []
            for exercise in response_json["exercises"]:
                exercise_list.append(
                    f"{exercise['type']}: {exercise['count']}"
                )
            return self.phrases_formats[state].format(
                f"On {date}", "\n".join(exercise_list)
            )
        elif state == "GET_MEALS":
            # Filling the response form with the response data.
            date = response_json["date"]
            meals_list = []
            for meals in response_json["meals"]:
                meals_list.append(meals + ":")
                for food in response_json["meals"][meals]:
                    meals_list.append(
                        f"{food}: {response_json['meals'][meals][food]} g"
                    )
            return self.phrases_formats[state].format(
                f"On {date}", "\n".join(meals_list)
            )
        elif state == "UPDATE_PARAMETERS":
            # Filling the response form with the response data and return the response.
            result = response_json["result"]
            return self.phrases_formats[state].format(result)
        elif state == "GET_STATS":
            # Filling the response form with the response data and return the response.
            stats_str = "\n".join([f"{stat} : {response_json[stat]}" for stat in response_json])
            return self.phrases_formats[state].format(stats_str)
        elif state == "KCALS_BURNED":
            # Filling the response form with the response data and return the response.
            date = response_json["date"]
            kcals_burned = response_json["kcals_burned"]
            return self.phrases_formats[state].format(f"On {date}", kcals_burned)
        elif state == "KCALS_GAINED":
            # Filling the response form with the response data and return the response.
            date = response_json["date"]
            kcals_gained = response_json["kcals_gained"]
            return self.phrases_formats[state].format(f"On {date}", kcals_gained)