import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ==========================================================================
  // Performance Optimizations
  // ==========================================================================
  
  // Enable React strict mode for better debugging
  reactStrictMode: true,
  
  // Compress responses
  compress: true,
  
  // Optimize images
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // Bundle optimization
  experimental: {
    // Enable optimized package imports for faster builds
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-icons',
      'date-fns',
    ],
  },
  
  // Headers for caching
  async headers() {
    return [
      {
        // Cache static assets
        source: '/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        // Cache API responses briefly
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=10, stale-while-revalidate=59',
          },
        ],
      },
    ];
  },
  
  // Reduce bundle size by not including server-only code in client
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{member}}',
    },
  },
};

export default nextConfig;
