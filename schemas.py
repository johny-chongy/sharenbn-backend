from flask_expects_json import

user_registration_schema = {

  "type": "object",
  "properties": {
    "username": { "type": "string" },
    "password": { "type": "string" },
    "first_name": { "type": "string" },
    "last_name": { "type": "string" },
    "email": { "type": "string" }
  },
  "required": [
    "username",
    "password",
    "first_name",
    "last_name",
    "email"
    ]

}