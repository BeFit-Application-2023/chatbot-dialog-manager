# Importing all needed modules.
import random


class RandomPhrase:
    def __init__(self, state_to_phrases_mapper : dict) -> None:
        '''
            The constructor of the RandomPhrase
                :param state_to_phrases_mapper: dict
                    The dictionary mapping the state to list of phrases.
        '''
        self.state_to_phrases_mapper = state_to_phrases_mapper
        self.servable_states = list(self.state_to_phrases_mapper.keys())

    def get_phrase(self, state : str) -> str:
        '''
            This function get a random response for the provided state.
                :param state: str
                    The state of the dialog FSM.
                :return: str
                    The chosen response.
        '''
        return random.choice(self.state_to_phrases_mapper[state])