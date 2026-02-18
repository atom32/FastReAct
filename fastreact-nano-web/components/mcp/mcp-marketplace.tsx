"use client"

import { MCPToolCard } from "./mcp-tool-card"

interface MCPTool {
  id: string
  name: string
  description: string
  categoryId: string
  version: string
  author: string
  installed: boolean
  rating: number
  downloads: string
  features: string[]
  installation: {
    command: string
    args: string[]
  }
  requirements: string[]
}

interface MCPMarketplaceProps {
  tools: MCPTool[]
}

export function MCPMarketplace({ tools }: MCPMarketplaceProps) {
  if (tools.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No tools found</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {tools.map((tool) => (
        <MCPToolCard key={tool.id} tool={tool} />
      ))}
    </div>
  )
}
