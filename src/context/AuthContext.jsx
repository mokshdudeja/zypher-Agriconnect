
import { createContext, useContext, useState, useEffect } from 'react'
import { 
  signOut,
  sendEmailVerification,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword
} from 'firebase/auth'
import { doc, getDoc, setDoc, updateDoc } from 'firebase/firestore'
import { auth, db } from '../lib/firebase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // Fetch profile from Firestore
        const profileRef = doc(db, 'profiles', firebaseUser.uid)
        const profileSnap = await getDoc(profileRef)
        const profileData = profileSnap.exists() ? profileSnap.data() : {}
        
        // If email is not verified, and user is not an admin, we sign out
        if (!firebaseUser.emailVerified && profileData.role !== 'admin') {
          setUser(null)
          setLoading(false)
          return
        }

        setUser({ ...firebaseUser, ...profileData, id: firebaseUser.uid })
      } else {
        setUser(null)
      }
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const login = async (email, password) => {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password)
      const firebaseUser = userCredential.user
      
      const profileSnap = await getDoc(doc(db, 'profiles', firebaseUser.uid))
      const profileData = profileSnap.exists() ? profileSnap.data() : {}
      
      // Admin bypass for email verification
      if (!firebaseUser.emailVerified && profileData.role !== 'admin') {
        await signOut(auth)
        return { success: false, error: 'verification_required' }
      }

      const fullUser = { ...firebaseUser, ...profileData, id: firebaseUser.uid }
      setUser(fullUser)
      return { success: true, user: fullUser }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const register = async ({ name, email, password, role, phone }) => {
    const avatars = { farmer: '👨‍🌾', wholesaler: '🏪', consumer: '🛒', admin: '🛡️' }
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password)
      const firebaseUser = userCredential.user
      
      // 1. Send verification email
      await sendEmailVerification(firebaseUser)

      const profileData = {
        name,
        role: role || 'consumer',
        phone,
        avatar: avatars[role] || '👤',
        created_at: new Date().toISOString()
      }
      
      // 2. Create profile in Firestore
      await setDoc(doc(db, 'profiles', firebaseUser.uid), profileData)
      
      // 3. Sign out immediately so they must verify and log in again
      await signOut(auth)
      setUser(null)
      
      return { success: true, needsVerification: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const resendVerification = async (email, password) => {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password)
      await sendEmailVerification(userCredential.user)
      await signOut(auth)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  const logout = async () => {
    await signOut(auth)
    setUser(null)
  }

  const updateProfile = async (updates) => {
    if (!user) return { success: false, error: 'Not logged in' }
    try {
      const profileRef = doc(db, 'profiles', user.id)
      await updateDoc(profileRef, {
        ...updates,
        updated_at: new Date().toISOString()
      })
      setUser(prev => ({ ...prev, ...updates }))
      return { success: true }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateProfile, resendVerification }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export default AuthContext
