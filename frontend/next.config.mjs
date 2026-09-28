import createNextIntlPlugin from 'next-intl/plugin';
const withNextIntl = createNextIntlPlugin('./i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  compress: true,

  // Tree-shake these large packages — only import what's actually used.
  // This reduces initial JS bundle size significantly.
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion", "recharts"],
  },

  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },

  // Silence the "missing src prop" warning from next/image in dev
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(nextConfig);
