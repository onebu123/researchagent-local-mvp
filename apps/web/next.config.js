/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    cpus: 1,
    turbopackMemoryLimit: 4096
  }
};

module.exports = nextConfig;
