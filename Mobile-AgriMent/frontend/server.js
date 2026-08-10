const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");
const { spawn } = require("child_process");

const app = express();
const API_TARGET = "http://127.0.0.1:8080";

const useTunnel = process.argv.includes("--tunnel") || process.env.TUNNEL === "1";

app.use("/api", createProxyMiddleware({ target: API_TARGET, changeOrigin: true }));
app.use("/uploads", createProxyMiddleware({ target: API_TARGET, changeOrigin: true }));
app.use("/health", createProxyMiddleware({ target: API_TARGET, changeOrigin: true }));

const METRO_PORT = 8082;
const EXPRESS_PORT = 8081;

app.use("/", createProxyMiddleware({ target: `http://127.0.0.1:${METRO_PORT}`, changeOrigin: true, ws: true }));

const metroArgs = ["start", "--port", String(METRO_PORT)];
if (useTunnel) {
  metroArgs.push("--tunnel");
} else {
  metroArgs.push("--host", "lan");
}

app.listen(EXPRESS_PORT, "0.0.0.0", () => {
  console.log("\n  ========================================");
  console.log("  AgriMent - All-in-One Server");
  console.log(`  Mode: ${useTunnel ? "Tunnel (ngrok)" : "LAN"}`);
  console.log(`  Phone URL: http://192.168.1.4:${EXPRESS_PORT}`);
  console.log("  API: localhost:8080");
  console.log(`  Metro: localhost:${METRO_PORT}`);
  console.log("  ========================================\n");
});

spawn("node", ["node_modules/.bin/expo", ...metroArgs], {
  cwd: __dirname,
  stdio: "inherit",
  shell: true,
}).on("close", () => process.exit(0));
