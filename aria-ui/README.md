# ZANA: Unified UI & Sensory Interface

This repository contains the visual and sensory entry points for the ZANA cognitive runtime.

## 📁 Repository Structure

*   **/landing**: The public marketing site for ZANA, built with Next.js 16, Framer Motion, and Three.js (2.5D Aeon Spaces). Deployable to [zana.vecanova.com](https://zana.vecanova.com).
*   **/app**: The Cognitive Cockpit (PWA). A high-performance interface for interacting with your Aeons via voice, vision, and text.
*   **/src-tauri**: Desktop distribution for Linux, macOS, and Windows. Wraps the PWA and the ZANA Gateway sidecar.

## 🚀 Features

*   **2.5D Aeon Dimension**: Gamified visualization of cognitive agent environments.
*   **AION Protocol Visualizer**: Real-time tensor-resonance pulse monitoring.
*   **Multimodal Sensors**: Integrated audio capture (Whisper) and vision gateway (Claude/LLaVA).
*   **Local-First Design**: Communicates directly with your ZANA Core over `localhost` (default) or a private LUMA node.

## 🛠️ Development

### Landing Page
\`\`\`bash
cd landing
npm install
npm run dev
\`\`\`

### Cognitive Cockpit (PWA)
\`\`\`bash
npm install
npm run dev
\`\`\`

### Desktop (Tauri)
\`\`\`bash
npm run tauri:dev
\`\`\`

## 🌐 Deployment

The landing page is optimized for production deployment on Vercel as a subdomain of \`vecanova.com\`.

---

Built with honor in Medellín, Colombia. 🇨🇴  
**[VECANOVA](https://vecanova.com)** · MIT License
