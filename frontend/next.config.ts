import type { NextConfig } from "next";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";

// Load the root .env (one directory up from frontend/) so NEXT_PUBLIC_* vars
// are available during `pnpm dev` and `pnpm build` without needing a local
// .env.local file inside the frontend folder.
const rootEnvPath = resolve(__dirname, "../.env");
if (existsSync(rootEnvPath)) {
  const lines = readFileSync(rootEnvPath, "utf-8").split("\n");
  for (const line of lines) {
    const match = line.match(/^\s*([^#\s][^=]*?)\s*=\s*(.*?)\s*$/);
    if (match) {
      const [, key, value] = match;
      // Don't overwrite vars already set in the environment (e.g. CI secrets)
      process.env[key] ??= value.replace(/^["']|["']$/g, "");
    }
  }
}

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
