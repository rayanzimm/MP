import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firestore():
    cred = credentials.Certificate(r'D:\Microsoft VS Code\MP\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
    firebase_admin.initialize_app(cred)
    return firestore.client()