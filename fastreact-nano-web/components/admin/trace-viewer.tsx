"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { RefreshCw } from "lucide-react"
import { gatewayApi } from "@/lib/gateway"

interface Trace {
  created_at: string
  session_id: string
  query?: string
  time_to_first_event_ms?: number
  time_to_final_ms?: number
  event_count?: number
  final_answer_length?: number
}

export function TraceViewer() {
  const [traces, setTraces] = useState<Trace[]>([])

  const load = async () => {
    const res = await fetch(gatewayApi("/api/traces"))
    if (res.ok) {
      const data = await res.json()
      setTraces(data.traces || [])
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Runtime Traces</CardTitle>
        <Button variant="outline" size="sm" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Session</TableHead>
                <TableHead>First Event</TableHead>
                <TableHead>Final</TableHead>
                <TableHead>Events</TableHead>
                <TableHead>Answer</TableHead>
                <TableHead>Query</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {traces.map((trace, index) => (
                <TableRow key={`${trace.session_id}-${trace.created_at}-${index}`}>
                  <TableCell className="whitespace-nowrap text-xs">{new Date(trace.created_at).toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-xs">{trace.session_id?.slice(0, 12)}...</TableCell>
                  <TableCell>{trace.time_to_first_event_ms ?? "-"}ms</TableCell>
                  <TableCell>{trace.time_to_final_ms ?? "-"}ms</TableCell>
                  <TableCell>{trace.event_count ?? "-"}</TableCell>
                  <TableCell>{trace.final_answer_length ?? "-"}</TableCell>
                  <TableCell className="max-w-md truncate">{trace.query || "-"}</TableCell>
                </TableRow>
              ))}
              {!traces.length && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground">No traces</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
