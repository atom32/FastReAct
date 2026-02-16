"use client"

import { ThemeProvider } from "@/lib/theme-context"
import { ChatInterface } from "@/components/chat/chat-interface"

export default function Page() {
  return (
    <ThemeProvider>
      <ChatInterface />
    </ThemeProvider>
  )
}
