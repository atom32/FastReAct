"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { RefreshCw } from "lucide-react"

interface AuditRecord {
  created_at: string
  session_id?: string
  request_id?: string
  tool_name: string
  decision_level: string
  decision_reason?: string
  approved?: boolean | null
  duration_ms?: number
}

export function AuditLog() {
  const [records, setRecords] = useState<AuditRecord[]>([])

  const load = async () => {
    const res = await fetch("http://localhost:9000/api/audit")
    if (res.ok) {
      const data = await res.json()
      setRecords(data.audit || [])
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Audit</CardTitle>
        <Button variant="outline" size="sm" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Tool</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Approved</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((record, index) => (
                <TableRow key={`${record.request_id || record.created_at}-${index}`}>
                  <TableCell className="whitespace-nowrap text-xs">{new Date(record.created_at).toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-sm">{record.tool_name}</TableCell>
                  <TableCell><Badge variant="outline">{record.decision_level}</Badge></TableCell>
                  <TableCell>{record.approved === null || record.approved === undefined ? "-" : record.approved ? "yes" : "no"}</TableCell>
                  <TableCell>{record.duration_ms ? `${record.duration_ms}ms` : "-"}</TableCell>
                  <TableCell className="max-w-md truncate">{record.decision_reason || "-"}</TableCell>
                </TableRow>
              ))}
              {!records.length && (
                <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground">No audit records</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
