"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dashboard } from "@/components/admin/dashboard"
import { ConfigEditor } from "@/components/admin/config-editor"
import { SessionManager } from "@/components/admin/session-manager"

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("dashboard")

  return (
    <div className="min-h-screen" style={{ background: "var(--fr-bg-primary)" }}>
      {/* Background Mesh */}
      <div className="background-mesh" />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 relative z-10">
        <div className="mb-6">
          <h1 className="text-3xl font-bold" style={{ color: "var(--fr-text-primary)" }}>
            Admin Dashboard
          </h1>
          <p className="mt-2" style={{ color: "var(--fr-text-secondary)" }}>
            Manage your FastReAct Nano instance
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <Dashboard />
          </TabsContent>

          <TabsContent value="sessions" className="space-y-6">
            <SessionManager />
          </TabsContent>

          <TabsContent value="config" className="space-y-6">
            <ConfigEditor />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
