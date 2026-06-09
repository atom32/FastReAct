"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"

export function ToolsPanel() {
  const [tools, setTools] = useState<string[]>([])
  const [mcpTools, setMcpTools] = useState<string[]>([])
  const [schemas, setSchemas] = useState<Array<{ name: string; description: string; parameters: string[] }>>([])
  const [servers, setServers] = useState<Array<{ name: string; alive: boolean }>>([])

  const load = async () => {
    const res = await fetch("http://localhost:9000/api/tools")
    if (res.ok) {
      const data = await res.json()
      setTools(data.tools || [])
      setMcpTools(data.mcp_tools || [])
      setSchemas(data.schemas || [])
      setServers(data.mcp_servers || [])
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
      <Card>
        <CardHeader><CardTitle>MCP Servers</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {servers.map((server) => (
            <Badge key={server.name} variant={server.alive ? "outline" : "destructive"}>
              {server.name}: {server.alive ? "running" : "stopped"}
            </Badge>
          ))}
          {!servers.length && <span className="text-sm text-muted-foreground">No MCP servers loaded</span>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Tool Schemas</CardTitle></CardHeader>
        <CardContent className="max-h-96 space-y-3 overflow-y-auto">
          {schemas.map((schema) => (
            <div key={schema.name} className="rounded-md border p-3">
              <div className="font-mono text-sm font-medium">{schema.name}</div>
              <div className="mt-1 text-sm text-muted-foreground">{schema.description}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {schema.parameters.map((param) => <Badge key={param} variant="outline">{param}</Badge>)}
              </div>
            </div>
          ))}
          {!schemas.length && <span className="text-sm text-muted-foreground">No schema data</span>}
        </CardContent>
      </Card>
    </div>
  )
}
