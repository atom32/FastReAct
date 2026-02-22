/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  // Disable React StrictMode to prevent double-rendering in development
  // This reduces duplicate log messages
  reactStrictMode: false,
}

export default nextConfig
