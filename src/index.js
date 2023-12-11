// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCwckzqjSuDBdPvFGmwxW_t86FMcaiFYOs",
  authDomain: "finsaver3.firebaseapp.com",
  projectId: "finsaver3",
  storageBucket: "finsaver3.appspot.com",
  messagingSenderId: "546832209179",
  appId: "1:546832209179:web:8be50246cdaf1bdc53efbe",
  measurementId: "G-365RF89GXF"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);