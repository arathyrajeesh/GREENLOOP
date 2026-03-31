import firebase_admin
from firebase_admin import credentials
import os
import json

def initialize_firebase():
    if firebase_admin._apps:
        return

    firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if firebase_json:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("firebase/serviceAccountKey.json")

    firebase_admin.initialize_app(cred)