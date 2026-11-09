/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hud: {
          bg: '#070a12',
          panel: '#0c1322',
          card: '#111b30',
          border: '#1e293b',
          cyan: '#00f0ff',
          amber: '#f59e0b',
          crimson: '#ff3366',
          emerald: '#00ffaa',
          purple: '#a855f7',
          blue: '#38bdf8'
        }
      },
      fontFamily: {
        mono: ['Fira Code', 'JetBrains Mono', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      animation: {
        'pulse-fast': 'pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-cyan': 'glowCyan 2s ease-in-out infinite alternate',
        'glow-crimson': 'glowCrimson 1.5s ease-in-out infinite alternate',
      },
      keyframes: {
        glowCyan: {
          '0%': { boxShadow: '0 0 5px rgba(0, 240, 255, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 240, 255, 0.6)' },
        },
        glowCrimson: {
          '0%': { boxShadow: '0 0 5px rgba(255, 51, 102, 0.3)' },
          '100%': { boxShadow: '0 0 25px rgba(255, 51, 102, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}
