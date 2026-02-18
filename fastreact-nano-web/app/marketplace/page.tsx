"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Search } from "lucide-react"
import { MCPMarketplace } from "@/components/mcp/mcp-marketplace"
import { mcpToolsData } from "@/lib/mcp-tools-data"

export default function MarketplacePage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("all")

  // Filter tools
  const filteredTools = mcpToolsData.tools.filter((tool) => {
    const matchesSearch =
      searchQuery === "" ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCategory =
      selectedCategory === "all" || tool.categoryId === selectedCategory

    return matchesSearch && matchesCategory
  })

  // Get installed tools
  const installedTools = mcpToolsData.tools.filter((t) => t.installed)

  return (
    <div className="min-h-screen bg-background">
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-8">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold">MCP Tool Marketplace</h1>
          <p className="text-muted-foreground mt-2">
            Discover and install Model Context Protocol tools
          </p>
        </div>
        {/* Search and Filter */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-full sm:w-[200px]">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {mcpToolsData.categories.map((cat) => (
                <SelectItem key={cat.id} value={cat.id}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Installed Tools Section */}
        {installedTools.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold mb-4">Installed Tools</h2>
            <MCPMarketplace tools={installedTools} />
          </section>
        )}

        {/* All Tools Section */}
        <section>
          <h2 className="text-xl font-semibold mb-4">
            {selectedCategory === "all" ? "All Tools" : mcpToolsData.categories.find((c) => c.id === selectedCategory)?.name}
            <span className="text-sm font-normal text-muted-foreground ml-2">
              ({filteredTools.length} tools)
            </span>
          </h2>
          <MCPMarketplace tools={filteredTools} />
        </section>
      </main>
    </div>
  )
}
