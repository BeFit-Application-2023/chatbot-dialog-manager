# Importing all needed modules.
from marshmallow import Schema, fields, ValidationError


class MessageSchema(Schema):
    # Defining the required schema fields.
    text = fields.Str(required=True)
    telegram_user_id = fields.Integer(required=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    username = fields.Str(required=True)
    chat_id = fields.Integer(required=True)

    def validate_json(self, json_data : dict):
        '''
            This function validates the requests body.
                :param json_data: dict
                    The request body.
                :returns: dict, int
                    Returns the validated json or the errors in the json
                    and the status code.
        '''
        try:
            result = self.load(json_data)
        except ValidationError as err:
            return err.messages, 400
        return result, 200
