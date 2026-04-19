
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "REMOVED_API_KEY",
  authDomain: "REMOVED authDomain",
  projectId: "REMOVED projectId",
  storageBucket: "REMOVED storageBucket",
  messagingSenderId: "REMOVED senderId",
  appId: "REMOVED appId"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export default app;
