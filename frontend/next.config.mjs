/** @type {import('next').NextConfig} */
const backend = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server bundle for a small container image.
  output: "standalone",
  // Proxy API calls to FastAPI so the admin session cookie stays first-party
  // (same origin as the app), which is what makes httponly + SameSite=Strict work.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
