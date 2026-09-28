import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy colors (kept for internal dashboard pages)
        warm: {
          bg: '#faf9f6',        
          surface: '#ffffff',   
          primary: '#f97316',   
          secondary: '#16a34a', 
          text: '#1f2937',      
          muted: '#6b7280',     
          border: '#e5e7eb',    
          hover: '#fff7ed',     
        },
        // Premium YUKTI tokens
        cream: {
          DEFAULT: '#FBF6ED',
          deep: '#F3E9D8',
        },
        ink: {
          DEFAULT: '#221D17',
          soft: '#55503F',
          faint: '#8A8272',
        },
        saffron: {
          DEFAULT: '#E17A2D',
          deep: '#C05F1C',
          tint: '#FBE7D4',
        },
        forest: {
          DEFAULT: '#38664A',
          deep: '#294C38',
          tint: '#E4EEE3',
        },
        'premium-border': {
          DEFAULT: '#E7DCC7',
          strong: '#D8C9AC',
        }
      },
      fontFamily: {
        sans: ['var(--font-jakarta)', 'ui-sans-serif', 'system-ui', 'sans-serif'], // Global sans is now Jakarta
        display: ['var(--font-fraunces)', 'ui-serif', 'serif'], // Fraunces for display headings
        devanagari: ['var(--font-noto-devanagari)', 'var(--font-jakarta)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 4px 20px rgba(34, 29, 23, 0.05)',
        'card-hover': '0 12px 30px rgba(34, 29, 23, 0.08)',
        'float': '0 20px 40px rgba(34, 29, 23, 0.1)',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
export default config;
