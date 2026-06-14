import { dirname } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  turbopack: {
    root: __dirname,
  },
  allowedDevOrigins: ["127.0.0.1"],
  // Disable React StrictMode to prevent double-rendering in development
  // This reduces duplicate log messages
  reactStrictMode: false,
}

export default nextConfig
