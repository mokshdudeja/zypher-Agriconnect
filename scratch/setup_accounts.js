
import { createClient } from '@supabase/supabase-js'
import fs from 'fs'

const envContent = fs.readFileSync('.env.local', 'utf8')
const supabaseUrl = envContent.match(/VITE_SUPABASE_URL=(.*)/)?.[1]
const supabaseKey = envContent.match(/VITE_SUPABASE_ANON_KEY=(.*)/)?.[1]

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseKey)

const accounts = [
  { role: 'admin', email: 'admin@agriconnect.com', password: 'admin@agriconnect', name: 'System Admin' },
  { role: 'farmer', email: 'farmer@agriconnect.com', password: 'farmer@agriconnect', name: 'Ravi Farmer' },
  { role: 'wholesaler', email: 'wholesaler@agriconnect.com', password: 'wholesaler@agriconnect', name: 'Mehta Wholesale' },
  { role: 'consumer', email: 'consumer@agriconnect.com', password: 'consumer@agriconnect', name: 'Aditya Consumer' },
]

async function createAccounts() {
  for (const acc of accounts) {
    console.log(`Creating user ${acc.email} (${acc.role})...`)
    
    const { data, error } = await supabase.auth.signUp({
      email: acc.email,
      password: acc.password,
      options: {
        data: {
          full_name: acc.name,
          role: acc.role
        }
      }
    })

    if (error) {
      if (error.message.includes('already registered')) {
        console.log(`User ${acc.email} already exists.`)
      } else {
        console.error(`Error creating ${acc.role}:`, error.message)
      }
    } else {
      console.log(`User ${acc.email} created successfully!`)
    }
  }
}

createAccounts()
