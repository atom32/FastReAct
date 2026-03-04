"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { useFastReActWS, type UserInfo } from "./use-fastreact-ws"

export function UserSettings() {
  // UserSettings 只需要用户认证功能，不需要事件回调
  // 传入空函数作为回调参数
  const { currentUser, login, logout } = useFastReActWS({
    onEvent: () => {},
    onUserMessage: () => {},
    onConfirmationRequired: () => {},
    onStatusChange: () => {},
    onError: () => {},
  })
  const [email, setEmail] = useState(currentUser.email || "")
  const [isOpen, setIsOpen] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    if (email && email.includes("@")) {
      login(email)
      setIsOpen(false)
    }
  }

  const handleLogout = () => {
    logout()
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="text-sm"
      >
        {currentUser.isLoggedIn ? (
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full" />
            {currentUser.email}
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-gray-400 rounded-full" />
            Guest
          </span>
        )}
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <Card className="absolute right-0 top-full mt-2 z-50 w-80 p-4 bg-white dark:bg-gray-800 border shadow-lg">
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">User Account</h3>
                {currentUser.isLoggedIn ? (
                  <div className="space-y-3">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      <p className="font-medium">{currentUser.email}</p>
                      <p className="text-xs mt-1">
                        Workspace: <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
                          {currentUser.userKey}
                        </code>
                      </p>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleLogout}
                      className="w-full"
                    >
                      Logout
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleLogin} className="space-y-3">
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium mb-1">
                        Email
                      </label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="user@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                    <Button type="submit" size="sm" className="w-full">
                      Login
                    </Button>
                    <p className="text-xs text-gray-500">
                      Your email is used to create a personal workspace for data isolation.
                    </p>
                  </form>
                )}
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
