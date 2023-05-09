# Importing all needed modules.
from datetime import datetime, timedelta
from dateutil import parser
import re


class DialogManager:
    def __init__(self, fsm) -> None:
        '''
            The constructor of the DialogManager class.
                :param fsm: dict
                    The dictionary representing the Final State Machine for the
                    dialog management.
        '''
        # Setting up the fields of the class.
        self.fsm = fsm
        # Defining the accepted intents as actions.
        self.accepted_actions = ["thank_you", "good", "goodbye", "greeting", "get_exercise",
                                 "get_meals", "get_goal_progress", "happy", "get_exercise_done",
                                 "update_parameters", "how_to_make_exercises", "get_stats",
                                 "kcals_burned", "kcals_gained", "angry", "tired"]

    def get_action_from_intent_and_ners(self,
                                        state : str,
                                        intent : str,
                                        ners : dict,
                                        accept_date : list = ["get_exercise", "get_meals", "kcals_burned", "kcals_gained"],
                                        accept_cardinal : list = ["update_parameters"],
                                        accept_nouns : list = ["update_parameters", "how_to_make_exercises"]):
        '''
            This function converts the intent and the Named Entities into a action for FSM.
                :param state: str
                    The string representing the state of the FSM.
                :param intent: str
                    The name of the intent of the message.
                :param ners: dict
                    All extracted Named Entities from the message.
                :param accept_date: list, default = ["get_exercise", "get_meals", "kcals_burned", "kcals_gained"]
                    The list of intent classes that accept DATE entities to form a action.
                :param accept_cardinal: list, default = ["update_parameters"]
                    The list of intent classes that accept CARDINAL entities to form a action.
                :param accept_nouns: list, default = ["update_parameters", "how_to_make_exercises"]
                    THe list of intent classes that accept NOUNS entities to form a action.
                :return: str
                    The name of the action.
        '''
        ners_to_add = []

        # Checking if the intent class accepts any entities and adds the to the list of ners.
        if intent in self.accepted_actions:
            if intent in accept_cardinal and "CARDINAL" in ners:
                ners_to_add.append("CARDINAL")
            if intent in accept_date and "DATE" in ners:
                ners_to_add.append("DATE")
            if intent in accept_nouns and "NOUNS" in ners:
                ners_to_add.append("NOUNS")
        else:
            # If the intent class doesn't require ners then find the action suitable for the last test.
            for state_action_pair in self.fsm:
                if state in state_action_pair:
                    action = state_action_pair[1]
                    params = re.findall("[A-Z]+", action)
                    if params:
                        ners_to_add = params.copy()
                        intent = ""
        # Joining the ners needed to create the action.
        addition = "&".join(ners_to_add)

        # Formulation of the action.
        action = f"{intent}[{addition}]" if addition else f"{intent}"
        return action

    def preprocess_date(self, date_string : str) -> str:
        '''
            This function converts multiple types of dates into the format: %d-%m-%Y
                :param date_string: str
                    The string representing the point in date.
                :return: str
                    The string representing the date in the %d-%m-%Y format.
        '''
        if date_string.lower() == "today":
            return datetime.now().strftime("%d-%m-%Y")
        elif date_string.lower() == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
        else:
            return parser.parse(date_string).strftime("%d-%m-%Y")

    def post_process_ners(self, ners : dict, interest_ners : list = ["DATE", "CARDINAL", "NOUNS"]):
        '''
            This function post-processes the detected Named Entities.
                :param ners: dict
                    The dictionary containing all detected named entities.
                :param interest_ners: list
                    The names of named entities of intnerest.
        '''
        # Filtering out the named entities that are not needed.
        ners = {ner : ners[ner] for ner in interest_ners if ner in ners}

        # Processing each named entity depending on it's type.
        if "DATE" in ners:
            for i in range(len(ners["DATE"])):
                ners["DATE"][i] = self.preprocess_date(ners["DATE"][i])
        if "CARDINAL" in ners:
            # Converting the cardinals into int or float.
            for i in range(len(ners["CARDINAL"])):
                if "." in ners["CARDINAL"][i]:
                    ners["CARDINAL"][i] = float(ners["CARDINAL"][i])
                else:
                    ners["CARDINAL"][i] = int(ners["CARDINAL"][i])
        if "NOUNS" in ners:
            # Filtering only the needed nouns.
            new_nouns = []
            for i in range(len(ners["NOUNS"])):
                if "weight" in ners["NOUNS"][i].lower():
                    new_nouns.append("weight")
                elif "height" in ners["NOUNS"][i].lower():
                    new_nouns.append("height")
            ners["NOUNS"] = new_nouns
        return ners

    def get_new_state(self, state : str, intent : str, ners : dict, sentiment : float = 0.5) -> str and dict:
        '''
            This function returns the new state and the post processes ners.
                :param state: str
                    The last state of the FSM.
                :param intent: str
                    The intent class of the message.
                :param ners: dict
                    The extracted named entities of the message.
                :param sentiment: float, default = 0.5
                    The predicted sentiment score of the message.
                    NOTE: At this version it is not used.
        '''
        # Getting the action based on the intent and named entities.
        action = self.get_action_from_intent_and_ners(state, intent, ners)

        # Post process the named entities.
        ners = self.post_process_ners(ners)
        print(f"ACTION - {action}")

        # Getting the new state of the dialog.
        if (state, action) in self.fsm:
            new_state = self.fsm[(state, action)]
        else:
            new_state = self.fsm[("ANY", action)]
        # Returning the new state and the named entities.
        return new_state, ners