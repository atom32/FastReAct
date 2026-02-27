import type { Metadata, Viewport } from "next"
import "./globals.css"

// 使用系统字体栈，不依赖 Google Fonts
// 这样即使不开梯子也能有好看的字体

export const metadata: Metadata = {
  title: "FastReAct Nano - AI Agent Interface",
  description: "A futuristic AI agent interface with multi-theme support and stunning visual effects",
}

export const viewport: Viewport = {
  themeColor: "#0a0e27",
  width: "device-width",
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
