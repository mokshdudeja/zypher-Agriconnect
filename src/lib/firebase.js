
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyCPqo6OEr8UwJV1RXce0It-ZR2Fjjz_WIo",
  authDomain: "agriconnect-zypher-db.firebaseapp.com",
  projectId: "agriconnect-zypher-db",
  storageBucket: "agriconnect-zypher-db.firebasestorage.app",
  messagingSenderId: "677338662330",
  appId: "1:677338662330:web:78d2206bd4c8d468498983"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export default app;
