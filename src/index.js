// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCZBItJceEEfX_o1zpS1tEkJA41Z1Xn6j8",
  authDomain: "finsaver2.firebaseapp.com",
  projectId: "finsaver2",
  storageBucket: "finsaver2.appspot.com",
  messagingSenderId: "216403614393",
  appId: "1:216403614393:web:5c18ca184902b5afe3d968",
  measurementId: "G-VTJWG3ZSMJ"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);