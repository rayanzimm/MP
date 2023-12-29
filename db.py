import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin import firestore
cred = credentials.Certificate(r'C:\Poly module\Year 3\MP\Website Code\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


