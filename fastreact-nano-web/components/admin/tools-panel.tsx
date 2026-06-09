"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"

export function ToolsPanel() {
  const [tools, setTools] = useState<string[]>([])
  const [mcpTools, setMcpTools] = useState<string[]>([])

  const load = async () => {
    const res = await fetch("http://localhost:9000/api/tools")
    if (res.ok) {
      const data = await res.json()
      setTools(data.tools || [])
      setMcpTools(data.mcp_tools || [])
    }
  }

  useEffect(() => {
    load()
  }, [])

  const nativeTools = tools.filter((tool) => !mcpTools.includes(tool))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Native Tools</CardTitle>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {nativeTools.map((tool) => <Badge key={tool} variant="outline">{tool}</Badge>)}
          {!nativeTools.length && <span className="text-sm text-muted-foreground">No native tools</span>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>MCP Tools</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {mcpTools.map((tool) => <Badge key={tool} variant="secondary">{tool}</Badge>)}
          {!mcpTools.length && <span className="text-sm text-muted-foreground">No MCP tools loaded</span>}
        </CardContent>
      </Card>
    </div>
  )
}
