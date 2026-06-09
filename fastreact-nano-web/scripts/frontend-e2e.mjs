import { chromium } from "playwright"
import fs from "node:fs/promises"

const webUrl = process.env.E2E_WEB_URL || "http://127.0.0.1:13000"
const gatewayWsUrl = process.env.E2E_GATEWAY_WS_URL || "ws://127.0.0.1:19000/ws"
const artifactDir = process.env.E2E_ARTIFACT_DIR || "../fastreact-nano/.fastreact/e2e"

async function ensureNoHorizontalOverflow(page, label) {
  const overflow = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    textLength: document.body.innerText.trim().length,
  }))
  if (overflow.textLength < 20) {
    throw new Error(`${label}: page appears blank`)
  }
  if (overflow.scrollWidth > overflow.width + 24) {
    throw new Error(`${label}: horizontal overflow ${overflow.scrollWidth} > ${overflow.width}`)
  }
}

async function wsRoundTrip(page) {
  return await page.evaluate((url) => new Promise((resolve, reject) => {
    const ws = new WebSocket(`${url}?user_key=web:e2e`)
    const timer = setTimeout(() => {
      ws.close()
      reject(new Error("WebSocket round-trip timed out"))
    }, 5000)
    const seen = []
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "ping" }))
      ws.send(JSON.stringify({ type: "control", action: "interrupt", reason: "E2E stop check" }))
      ws.send(JSON.stringify({ type: "control", action: "approve_tool", request_id: "e2e-missing" }))
      ws.send(JSON.stringify({ type: "control", action: "deny_tool", request_id: "e2e-missing", reason: "E2E deny check" }))
    }
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      seen.push(message.type)
      if (seen.includes("pong") && seen.includes("tool_approval")) {
        clearTimeout(timer)
        ws.close()
        resolve(seen)
      }
    }
    ws.onerror = () => {
      clearTimeout(timer)
      reject(new Error("WebSocket error"))
    }
  }), gatewayWsUrl)
}

async function runViewport(browser, viewport, name) {
  const context = await browser.newContext({ viewport })
  const page = await context.newPage()
  page.setDefaultTimeout(10000)
  page.on("console", (message) => {
    if (message.type() === "error") {
      console.error(`[browser:${name}] ${message.text()}`)
    }
  })
  page.on("pageerror", (error) => {
    console.error(`[pageerror:${name}] ${error.message}`)
  })

  await page.goto(webUrl, { waitUntil: "networkidle" })
  const input = page.getByPlaceholder(/Send a message/i)
  if (await input.count()) {
    await input.fill(`E2E ${name}`)
    await page.getByRole("button", { name: /Send message/i }).click()
    await page.getByText(`E2E ${name}`).waitFor()
  } else {
    await page.getByRole("button", { name: /Analyze code/i }).click()
    await page.getByText(/Analyze this React component/i).waitFor()
  }
  await wsRoundTrip(page)
  await ensureNoHorizontalOverflow(page, `${name} chat`)
  await page.screenshot({ path: `${artifactDir}/chat-${name}.png`, fullPage: true })

  await page.goto(`${webUrl}/admin`, { waitUntil: "networkidle" })
  const tabs = ["Dashboard", "Sessions", "Tasks", "Tools/MCP", "Audit", "Traces", "Configuration"]
  for (const tab of tabs) {
    await page.getByRole("tab", { name: tab }).click()
    await page.waitForTimeout(250)
    await ensureNoHorizontalOverflow(page, `${name} admin ${tab}`)
  }

  await page.getByRole("tab", { name: "Tasks" }).click()
  const title = `E2E task ${Date.now()}`
  await page.getByPlaceholder("New task title").fill(title)
  await page.getByRole("button", { name: /Create/i }).click()
  await page.getByText(title).waitFor()
  await page.getByRole("button", { name: /Start/i }).first().click()
  await page.getByText("in_progress").first().waitFor()
  await page.screenshot({ path: `${artifactDir}/admin-${name}.png`, fullPage: true })

  await context.close()
}

await fs.mkdir(artifactDir, { recursive: true })

let browser
try {
  browser = await chromium.launch({ channel: "chrome", headless: true })
} catch {
  browser = await chromium.launch({ headless: true })
}

try {
  await runViewport(browser, { width: 1440, height: 1000 }, "desktop")
  await runViewport(browser, { width: 390, height: 844 }, "mobile")
  console.log(`[frontend-e2e] screenshots written to ${artifactDir}`)
} catch (error) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  try {
    await page.goto(webUrl, { waitUntil: "domcontentloaded" })
    await page.screenshot({ path: `${artifactDir}/failure.png`, fullPage: true })
    const text = await page.locator("body").innerText().catch(() => "")
    console.error(`[frontend-e2e] failure page text:\n${text.slice(0, 2000)}`)
  } finally {
    await context.close()
  }
  throw error
} finally {
  await browser.close()
}
