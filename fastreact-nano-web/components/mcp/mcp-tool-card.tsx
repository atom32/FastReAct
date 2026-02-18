"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Star, Download, ExternalLink, Settings, Check } from "lucide-react"

interface MCPTool {
  id: string
  name: string
  description: string
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

interface MCPToolCardProps {
  tool: MCPTool
}

export function MCPToolCard({ tool }: MCPToolCardProps) {
  const [installed, setInstalled] = useState(tool.installed)
  const [detailsOpen, setDetailsOpen] = useState(false)

  const handleInstall = () => {
    // TODO: Implement actual installation
    setInstalled(!installed)
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{tool.name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">{tool.description}</p>
          </div>
          {installed && (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <Check className="h-3 w-3 mr-1" />
              Installed
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
            <span>{tool.rating}</span>
          </div>
          <div className="flex items-center gap-1">
            <Download className="h-4 w-4" />
            <span>{tool.downloads}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            onClick={handleInstall}
            variant={installed ? "outline" : "default"}
            className="flex-1"
          >
            {installed ? "Remove" : "Install"}
          </Button>
          <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="icon">
                <ExternalLink className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{tool.name}</DialogTitle>
                <DialogDescription>{tool.description}</DialogDescription>
              </DialogHeader>
              <Tabs defaultValue="features" className="mt-4">
                <TabsList>
                  <TabsTrigger value="features">Features</TabsTrigger>
                  <TabsTrigger value="installation">Installation</TabsTrigger>
                  <TabsTrigger value="requirements">Requirements</TabsTrigger>
                </TabsList>
                <TabsContent value="features" className="space-y-2">
                  <ul className="space-y-2">
                    {tool.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Check className="h-4 w-4 text-green-500 mt-0.5" />
                        <span className="text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </TabsContent>
                <TabsContent value="installation" className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-2">Command:</p>
                    <code className="block bg-muted p-3 rounded text-sm">
                      {tool.installation.command} {tool.installation.args.join(" ")}
                    </code>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p>Run this command in your terminal to install the tool.</p>
                  </div>
                </TabsContent>
                <TabsContent value="requirements" className="space-y-2">
                  <ul className="space-y-2">
                    {tool.requirements.map((req, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Settings className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <span className="text-sm">{req}</span>
                      </li>
                    ))}
                  </ul>
                </TabsContent>
              </Tabs>
            </DialogContent>
          </Dialog>
        </div>

        {/* Meta */}
        <div className="text-xs text-muted-foreground">
          v{tool.version} • by {tool.author}
        </div>
      </CardContent>
    </Card>
  )
}
