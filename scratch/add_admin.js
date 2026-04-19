
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'

const envContent = fs.readFileSync('.env.local', 'utf8')
const supabaseUrl = envContent.match(/VITE_SUPABASE_URL=(.*)/)?.[1]
const supabaseKey = envContent.match(/VITE_SUPABASE_ANON_KEY=(.*)/)?.[1]

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase credentials in .env')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseKey)

async function createAdmin() {
  const email = 'admin@agriconnect.com'
  const password = 'admin@agriconnect'
  const name = 'System Admin'
  const role = 'admin'

  console.log(`Creating user ${email}...`)
  
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: name,
        role
      }
    }
  })

  if (error) {
    if (error.message.includes('already registered')) {
      console.log('Admin user already exists.')
    } else {
      console.error('Error creating admin:', error.message)
    }
  } else {
    console.log('Admin user created successfully!')
    console.log('User ID:', data.user?.id)
  }
}

createAdmin()
