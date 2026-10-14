/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  /** 便于 Docker / 服务器单机部署 `node server.js` */
  output: 'standalone',
  /** 浏览器走 /api/backend/* → app/api/backend/[...path]/route.ts（长请求如 quarter/start 不用 rewrites，避免 ~30s 断连） */
  async rewrites() {
    return [];
  },
};

export default nextConfig;

