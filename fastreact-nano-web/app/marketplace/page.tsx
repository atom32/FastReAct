"use client"

import { useState, useEffect } from "react"
import { Navigation } from "@/components/navigation"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Search, RefreshCw } from "lucide-react"
import { MCPMarketplace } from "@/components/mcp/mcp-marketplace"

interface MCPServer {
  name: string
  command: string
  args: string[]
  description: string
  isolation: string
  associated_skill: string | null
}

interface MCPServerResponse {
  servers: MCPServer[]
  count: number
}

export default function MarketplacePage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("all")
  const [installedServers, setInstalledServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // Fetch installed MCP servers from Gateway
  const fetchServers = async () => {
    try {
      const response = await fetch("http://localhost:9000/api/mcp/servers")
      if (response.ok) {
        const data: MCPServerResponse = await response.json()
        setInstalledServers(data.servers)
      }
    } catch (error) {
      console.error("Failed to fetch MCP servers:", error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchServers()
    const interval = setInterval(fetchServers, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchServers()
  }

  // Filter installed servers
  const filteredServers = installedServers.filter((server) => {
    const matchesSearch =
      searchQuery === "" ||
      server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      server.description.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCategory =
      selectedCategory === "all" ||
      (selectedCategory === "installed" && server.isolation) ||
      (selectedCategory === server.isolation)

    return matchesSearch && matchesCategory
  })

  return (
    <div className="min-h-screen" style={{ background: "var(--fr-bg-primary)" }}>
      {/* Navigation */}
      <Navigation />

      {/* Background Mesh */}
      <div className="background-mesh" />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-8 relative z-10">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold" style={{ color: "var(--fr-text-primary)" }}>
              MCP Tool Marketplace
            </h1>
            <p className="mt-2" style={{ color: "var(--fr-text-secondary)" }}>
              Manage your Model Context Protocol servers
            </p>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Status Bar */}
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            {installedServers.length} Servers Installed
          </Badge>
          {loading && (
            <span className="text-sm text-muted-foreground">Loading...</span>
          )}
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search servers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-full sm:w-[200px]">
              <SelectValue placeholder="Filter by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Servers</SelectItem>
              <SelectItem value="shared">Shared</SelectItem>
              <SelectItem value="lazy_per_user">Lazy Per User</SelectItem>
              <SelectItem value="per_user">Per User</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Installed Servers Section */}
        {installedServers.length > 0 ? (
          <section>
            <h2 className="text-xl font-semibold mb-4">
              Installed Servers
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({filteredServers.length} / {installedServers.length})
              </span>
            </h2>
            <MCPMarketplace
              tools={filteredServers.map((server) => ({
                id: server.name,
                name: server.name,
                description: server.description,
                categoryId: server.isolation,
                version: "1.0.0",
                author: "FastReAct",
                installed: true,
                rating: 4.5,
                downloads: "N/A",
                features: [],
                installation: {
                  command: server.command,
                  args: server.args,
                },
                requirements: [],
                isolation: server.isolation,
                associatedSkill: server.associated_skill,
              }))}
            />
          </section>
        ) : (
          <section className="text-center py-12">
            <p className="text-muted-foreground">
              {loading ? "Loading MCP servers..." : "No MCP servers installed"}
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Configure servers in ~/.fastreact/config.json
            </p>
          </section>
        )}
      </main>
    </div>
  )
}
