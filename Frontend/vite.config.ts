import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig, loadEnv } from 'vite'
import { createGateway } from './server/gateway.ts'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }
  const gateway = createGateway({
    backendUrl: env.BACKEND_URL || 'http://127.0.0.1:8000',
    apiKey: env.BACKEND_API_KEY,
    username: env.DEMO_ACCESS_USER,
    password: env.DEMO_ACCESS_PASSWORD,
  })
  return {
  server: { host: '127.0.0.1' },
  plugins: [
    {
      name: 'ancla-server-gateway',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          gateway(req, res).then(handled => { if (!handled) next() }).catch(next)
        })
      },
    },
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  }
})
