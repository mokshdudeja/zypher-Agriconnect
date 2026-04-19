import { useState } from 'react'
import { Search, Filter, MoreVertical } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { adminUsers } from '../../data/mockData'

export default function UserManagement() {
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('All')

  const roles = ['All', 'Farmer', 'Wholesaler', 'Consumer']
  const filtered = adminUsers.filter(u => {
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())
    const matchRole = roleFilter === 'All' || u.role === roleFilter
    return matchSearch && matchRole
  })

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">User Management</h1>
        <p className="text-slate-500 mt-1">{adminUsers.length} total users</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 animate-fade-in-up delay-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search users..."
            className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm"
          />
        </div>
        <div className="flex gap-2">
          {roles.map(r => (
            <button
              key={r}
              onClick={() => setRoleFilter(r)}
              className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                roleFilter === r ? 'bg-slate-800 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <Card className="animate-fade-in-up delay-2">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">User</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Role</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Joined</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase hidden sm:table-cell">Orders</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Status</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((user) => (
                <tr key={user.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                        user.role === 'Farmer' ? 'bg-leaf-600' :
                        user.role === 'Wholesaler' ? 'bg-harvest-600' : 'bg-sky-600'
                      }`}>
                        {user.name[0]}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">{user.name}</p>
                        <p className="text-xs text-slate-400">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <Badge variant={user.role === 'Farmer' ? 'success' : user.role === 'Wholesaler' ? 'warning' : 'info'}>
                      {user.role}
                    </Badge>
                  </td>
                  <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{user.joinDate}</td>
                  <td className="px-5 py-4 font-medium text-slate-700 hidden sm:table-cell">{user.orders}</td>
                  <td className="px-5 py-4">
                    <Badge variant={
                      user.status === 'Verified' ? 'success' :
                      user.status === 'Active' ? 'info' : 'pending'
                    }>
                      {user.status}
                    </Badge>
                  </td>
                  <td className="px-5 py-4">
                    <button className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors">
                      <MoreVertical className="w-4 h-4 text-slate-500" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
