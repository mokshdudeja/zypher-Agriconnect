
import { auth, db } from './src/lib/firebase.js';
import { 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';

const users = [
  {
    email: 'admin@agriconnect.com',
    password: 'admin@agriconnect',
    name: 'System Admin',
    role: 'admin',
    phone: '1234567890'
  },
  {
    email: 'farmer@agriconnect.com',
    password: 'admin@agriconnect',
    name: 'Ravi Farmer',
    role: 'farmer',
    phone: '9876543210'
  },
  {
    email: 'wholesaler@agriconnect.com',
    password: 'admin@agriconnect',
    name: 'Arjun Wholesaler',
    role: 'wholesaler',
    phone: '8765432109'
  },
  {
    email: 'consumer@agriconnect.com',
    password: 'admin@agriconnect',
    name: 'Priya Consumer',
    role: 'consumer',
    phone: '7654321098'
  }
];

const avatars = { farmer: '👨‍🌾', wholesaler: '🏪', consumer: '🛒', admin: '🛡️' };

async function setup() {
  console.log('🚀 Starting Firebase Account Setup...');
  
  for (const user of users) {
    try {
      console.log(`Creating user: ${user.email}...`);
      const cred = await createUserWithEmailAndPassword(auth, user.email, user.password);
      
      const profileData = {
        name: user.name,
        role: user.role,
        phone: user.phone,
        avatar: avatars[user.role] || '👤',
        created_at: new Date().toISOString()
      };
      
      await setDoc(doc(db, 'profiles', cred.user.uid), profileData);
      console.log(`✅ Success for ${user.email}`);
      
      // We need to sign out because createUserWithEmailAndPassword signs the user in automatically
      await signOut(auth);
    } catch (err) {
      if (err.code === 'auth/email-already-in-use') {
        console.log(`⚠️ User ${user.email} already exists.`);
      } else {
        console.error(`❌ Error for ${user.email}:`, err.message);
      }
    }
  }
  
  console.log('✨ Setup complete!');
  process.exit(0);
}

setup();
