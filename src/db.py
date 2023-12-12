import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate(r'C:\Poly module\Year 3\MP\Website Code\MP\src\finsaver3-firebase-adminsdk-udjjx-b479ad6c2d.json')
firebase_admin.initialize_app(cred)
db = firestore.client()
data = {
    'task': 'wash the dishes',
    'status': 'todo'
}

doc_ref = db.collection('taskCollection').document()
doc_ref.set(data)

print('Document ID:', doc_ref.id)