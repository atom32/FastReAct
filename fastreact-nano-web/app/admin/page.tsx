"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Navigation } from "@/components/navigation"
import { Dashboard } from "@/components/admin/dashboard"
import { ConfigEditor } from "@/components/admin/config-editor"
import { SessionManager } from "@/components/admin/session-manager"
import { TaskBoard } from "@/components/admin/task-board"
import { ToolsPanel } from "@/components/admin/tools-panel"
import { AuditLog } from "@/components/admin/audit-log"
import { TraceViewer } from "@/components/admin/trace-viewer"

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("dashboard")

  return (
    <div className="min-h-screen" style={{ background: "var(--fr-bg-primary)" }}>
      {/* Navigation */}
      <Navigation />

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
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 lg:w-[980px]">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
            <TabsTrigger value="tools">Tools/MCP</TabsTrigger>
            <TabsTrigger value="audit">Audit</TabsTrigger>
            <TabsTrigger value="traces">Traces</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <Dashboard />
          </TabsContent>

          <TabsContent value="sessions" className="space-y-6">
            <SessionManager />
          </TabsContent>

          <TabsContent value="tasks" className="space-y-6">
            <TaskBoard />
          </TabsContent>

          <TabsContent value="tools" className="space-y-6">
            <ToolsPanel />
          </TabsContent>

          <TabsContent value="audit" className="space-y-6">
            <AuditLog />
          </TabsContent>

          <TabsContent value="traces" className="space-y-6">
            <TraceViewer />
          </TabsContent>

          <TabsContent value="config" className="space-y-6">
            <ConfigEditor />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
