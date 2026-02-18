"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save, RotateCcw, Download, Upload } from "lucide-react"

interface LLMConfig {
  provider: string
  model: string
  api_key: string
  base_url: string
  temperature: number
  max_tokens: number
}

interface Config {
  llm: LLMConfig
  mcp_servers: any[]
  tools: string[]
  system_prompt: string
  max_iterations: number
}

export function ConfigEditor() {
  const [config, setConfig] = useState<Config>({
    llm: {
      provider: "openai",
      model: "gpt-4o-mini",
      api_key: "",
      base_url: "https://api.openai.com/v1",
      temperature: 0.7,
      max_tokens: 4096,
    },
    mcp_servers: [],
    tools: [],
    system_prompt: "",
    max_iterations: 10,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch("http://localhost:9000/api/config")
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      }
    } catch (error) {
      console.error("Failed to fetch config:", error)
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      const response = await fetch("http://localhost:9000/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      })
      if (response.ok) {
        alert("Configuration saved successfully")
      }
    } catch (error) {
      console.error("Failed to save config:", error)
      alert("Failed to save configuration")
    } finally {
      setSaving(false)
    }
  }

  const resetConfig = () => {
    if (confirm("Reset to default configuration?")) {
      fetchConfig()
    }
  }

  const exportConfig = () => {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "fastreact-config.json"
    a.click()
  }

  if (loading) {
    return <div className="text-center py-8">Loading configuration...</div>
  }

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="flex gap-2">
        <Button onClick={saveConfig} disabled={saving}>
          <Save className="h-4 w-4 mr-2" />
          {saving ? "Saving..." : "Save Configuration"}
        </Button>
        <Button onClick={resetConfig} variant="outline">
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset
        </Button>
        <Button onClick={exportConfig} variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Configuration Tabs */}
      <Tabs defaultValue="llm" className="space-y-4">
        <TabsList>
          <TabsTrigger value="llm">LLM Settings</TabsTrigger>
          <TabsTrigger value="mcp">MCP Servers</TabsTrigger>
          <TabsTrigger value="agent">Agent Settings</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="llm" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Language Model Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Provider</Label>
                <Select
                  value={config.llm.provider}
                  onValueChange={(value) =>
                    setConfig({ ...config, llm: { ...config.llm, provider: value } })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Model</Label>
                <Input
                  value={config.llm.model}
                  onChange={(e) =>
                    setConfig({ ...config, llm: { ...config.llm, model: e.target.value } })
                  }
                  placeholder="gpt-4o-mini"
                />
              </div>

              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  type="password"
                  value={config.llm.api_key}
                  onChange={(e) =>
                    setConfig({ ...config, llm: { ...config.llm, api_key: e.target.value } })
                  }
                  placeholder="sk-..."
                />
              </div>

              <div className="space-y-2">
                <Label>Base URL</Label>
                <Input
                  value={config.llm.base_url}
                  onChange={(e) =>
                    setConfig({ ...config, llm: { ...config.llm, base_url: e.target.value } })
                  }
                  placeholder="https://api.openai.com/v1"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Temperature</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={config.llm.temperature}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        llm: { ...config.llm, temperature: parseFloat(e.target.value) },
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    value={config.llm.max_tokens}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        llm: { ...config.llm, max_tokens: parseInt(e.target.value) },
                      })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mcp">
          <Card>
            <CardHeader>
              <CardTitle>MCP Servers</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Manage MCP servers from the Marketplace page.
              </p>
              <a href="/marketplace" className="text-sm text-primary hover:underline">
                Go to Marketplace →
              </a>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agent">
          <Card>
            <CardHeader>
              <CardTitle>Agent Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Max Iterations</Label>
                <Input
                  type="number"
                  value={config.max_iterations}
                  onChange={(e) =>
                    setConfig({ ...config, max_iterations: parseInt(e.target.value) })
                  }
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Advanced configuration options coming soon.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
