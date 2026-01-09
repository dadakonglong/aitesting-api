/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        NEXT_PUBLIC_AI_API_URL: process.env.NEXT_PUBLIC_AI_API_URL || 'http://localhost:8000',
        NEXT_PUBLIC_EXEC_API_URL: process.env.NEXT_PUBLIC_EXEC_API_URL || 'http://localhost:8000',
    },
}

module.exports = nextConfig
