<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Local Chat UI Example (React + Vite)

This example UI now defaults to the local FastAPI backend instead of Gemini. You can switch providers via environment variables without touching components.

## Prerequisites
- Node.js 18+
- Backend running at `http://localhost:8030` (or another host you set in env)

## Setup
1. Install dependencies:
   ```bash
   npm install
   ```
2. Copy the example environment file and adjust values as needed:
   ```bash
   cp .env.example .env
   ```
   - `VITE_BACKEND_URL`: FastAPI backend base URL (default `http://localhost:8030`).
   - `VITE_PROVIDER`: `fastapi` (default) or `gemini`.
   - `VITE_GEMINI_API_KEY`: required only when using the Gemini provider.
   - `VITE_CHAT_DEBUG`: optional flag for verbose client-side logging in dev.
3. Run the app:
   ```bash
   npm run dev
   ```

## Provider switching
- Local FastAPI (default): `VITE_PROVIDER=fastapi`
- Gemini: `VITE_PROVIDER=gemini` and set `VITE_GEMINI_API_KEY`

The UI selects the provider at startup via configuration, so you can toggle behaviors without modifying the component tree.
