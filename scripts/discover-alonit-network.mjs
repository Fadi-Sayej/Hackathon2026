import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const OUTPUT_ROOT = path.join("data", "debug", "network");

const PRODUCT_KEYS = [
  "name",
  "item",
  "product",
  "price",
  "barcode",
  "category",
  "availability",
  "inStock",
  "menu",
  "catalog",
];

const DEFAULT_TARGETS = [
  {
    sourceId: "alonit_kafr_qasim",
    url: "https://easy.co.il/en/list/Alonit?region=1058",
  },
  {
    sourceId: "super_alonit_einat_easy",
    url: "https://easy.co.il/en/page/26797254",
  },
  {
    sourceId: "super_alonit_einat_wolt",
    url: "https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat/items/menucategory-107",
  },
];

const IGNORE_CONTENT_TYPES = [
  "image/",
  "font/",
  "text/css",
  "application/font",
  "application/octet-stream",
];

const IGNORE_EXTENSIONS = /\.(avif|bmp|css|gif|ico|jpe?g|otf|png|svg|ttf|webp|woff2?)($|[?#])/i;

const LINK_HINTS = [
  "online order",
  "order",
  "delivery",
  "deliveries",
  "price list",
  "catalog",
  "menu",
  "wolt",
  "selfpoint",
  "משלוח",
  "משלוחים",
  "הזמנה",
  "מחירון",
  "תפריט",
];

function parseArgs(argv) {
  const options = {
    headed: false,
    maxLinkedPages: 4,
    waitMs: 4500,
    targets: [],
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--headed") {
      options.headed = true;
    } else if (arg.startsWith("--max-linked=")) {
      options.maxLinkedPages = Number.parseInt(arg.split("=")[1], 10);
    } else if (arg === "--max-linked") {
      options.maxLinkedPages = Number.parseInt(argv[++i], 10);
    } else if (arg.startsWith("--wait-ms=")) {
      options.waitMs = Number.parseInt(arg.split("=")[1], 10);
    } else if (arg === "--wait-ms") {
      options.waitMs = Number.parseInt(argv[++i], 10);
    } else if (arg.startsWith("--url=")) {
      options.targets.push(parseTargetArg(arg.slice("--url=".length)));
    } else if (arg === "--url") {
      options.targets.push(parseTargetArg(argv[++i]));
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  options.maxLinkedPages = Number.isFinite(options.maxLinkedPages)
    ? Math.max(0, options.maxLinkedPages)
    : 4;
  options.waitMs = Number.isFinite(options.waitMs) ? Math.max(0, options.waitMs) : 4500;

  return options;
}

function parseTargetArg(value) {
  const separatorIndex = value.indexOf("=");
  if (separatorIndex === -1) {
    const url = value;
    return { sourceId: sourceIdFromUrl(url), url };
  }

  return {
    sourceId: sanitizeSourceId(value.slice(0, separatorIndex)),
    url: value.slice(separatorIndex + 1),
  };
}

function sourceIdFromUrl(url) {
  try {
    const parsed = new URL(url);
    return sanitizeSourceId(parsed.hostname.replace(/^www\./, ""));
  } catch {
    return "custom_source";
  }
}

function sanitizeSourceId(value) {
  return value.toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
}

function printHelp() {
  console.log(`Usage:
  npm run discover:alonit-network
  node scripts/discover-alonit-network.mjs --headed --max-linked 6
  node scripts/discover-alonit-network.mjs --url alonit_kafr_qasim=https://example.com/catalog

Output:
  data/debug/network/<source_id>/*.json
  data/debug/network/<source_id>/summary.csv`);
}

function shouldIgnore(response) {
  const contentType = response.headers()["content-type"]?.toLowerCase() ?? "";
  const url = response.url();
  return IGNORE_EXTENSIONS.test(url) || IGNORE_CONTENT_TYPES.some((type) => contentType.includes(type));
}

function isLikelyJson(response, body) {
  const contentType = response.headers()["content-type"]?.toLowerCase() ?? "";
  if (contentType.includes("json")) {
    return true;
  }

  const prefix = body.toString("utf8", 0, Math.min(body.length, 64)).trimStart();
  return prefix.startsWith("{") || prefix.startsWith("[");
}

function collectMatchedKeys(value, matched = new Set()) {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectMatchedKeys(item, matched);
    }
    return matched;
  }

  if (!value || typeof value !== "object") {
    return matched;
  }

  for (const [key, child] of Object.entries(value)) {
    const normalizedKey = key.toLowerCase();
    for (const productKey of PRODUCT_KEYS) {
      if (normalizedKey.includes(productKey.toLowerCase())) {
        matched.add(productKey);
      }
    }
    collectMatchedKeys(child, matched);
  }

  return matched;
}

function scoreCandidate(parsedJson) {
  const matchedKeys = [...collectMatchedKeys(parsedJson)];
  let score = matchedKeys.length;

  if (matchedKeys.length === 0) {
    return {
      matchedKeys,
      score: 0,
    };
  }

  if (Array.isArray(parsedJson)) {
    score += Math.min(parsedJson.length, 10) / 10;
  } else if (parsedJson && typeof parsedJson === "object") {
    const rootKeys = Object.keys(parsedJson).join(" ").toLowerCase();
    if (rootKeys.includes("items") || rootKeys.includes("products")) {
      score += 1;
    }
  }

  return {
    matchedKeys,
    score: Number(score.toFixed(2)),
  };
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`;
  }
  return text;
}

async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 600;
      const timer = setInterval(() => {
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= document.body.scrollHeight || totalHeight >= 8000) {
          clearInterval(timer);
          resolve();
        }
      }, 250);
    });
  });
}

async function discoverLinkedPages(page, currentUrl, maxLinkedPages) {
  if (maxLinkedPages <= 0) {
    return [];
  }

  const links = await page.evaluate((hints) => {
    return [...document.querySelectorAll("a[href]")]
      .map((anchor) => ({
        href: anchor.href,
        text: (anchor.textContent || "").trim(),
        aria: anchor.getAttribute("aria-label") || "",
      }))
      .filter((link) => {
        const haystack = `${link.href} ${link.text} ${link.aria}`.toLowerCase();
        return hints.some((hint) => haystack.includes(hint.toLowerCase()));
      });
  }, LINK_HINTS);

  const seen = new Set([currentUrl]);
  const result = [];
  for (const link of links) {
    if (!link.href || seen.has(link.href)) {
      continue;
    }
    seen.add(link.href);
    result.push(link.href);
    if (result.length >= maxLinkedPages) {
      break;
    }
  }
  return result;
}

async function visitUrl(page, url, waitMs) {
  console.log(`Opening ${url}`);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
  await autoScroll(page).catch(() => {});
  if (waitMs > 0) {
    await page.waitForTimeout(waitMs);
  }
}

async function runTarget(browser, target, options) {
  const outputDir = path.join(OUTPUT_ROOT, target.sourceId);
  await mkdir(outputDir, { recursive: true });

  const context = await browser.newContext({
    locale: "he-IL",
    timezoneId: "Asia/Jerusalem",
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
  });
  const page = await context.newPage();
  const summary = [];
  const savedUrls = new Set();

  page.on("response", async (response) => {
    const request = response.request();
    const resourceType = request.resourceType();
    if (!["fetch", "xhr"].includes(resourceType) || shouldIgnore(response)) {
      return;
    }

    const url = response.url();
    const contentType = response.headers()["content-type"] ?? "";
    let body;
    try {
      body = await response.body();
    } catch (error) {
      summary.push({
        url,
        status: response.status(),
        contentType,
        responseSize: 0,
        matchedKeys: [],
        candidateScore: 0,
        error: error.message,
      });
      return;
    }

    const row = {
      url,
      status: response.status(),
      contentType,
      responseSize: body.length,
      matchedKeys: [],
      candidateScore: 0,
      error: "",
    };

    if (isLikelyJson(response, body)) {
      try {
        const parsed = JSON.parse(body.toString("utf8"));
        const { matchedKeys, score } = scoreCandidate(parsed);
        row.matchedKeys = matchedKeys;
        row.candidateScore = score;

        if (!savedUrls.has(url)) {
          savedUrls.add(url);
          const hash = crypto.createHash("sha1").update(url).digest("hex").slice(0, 12);
          const fileName = `${String(savedUrls.size).padStart(3, "0")}-${hash}.json`;
          await writeFile(path.join(outputDir, fileName), `${JSON.stringify(parsed, null, 2)}\n`);
        }
      } catch (error) {
        row.error = `json_parse_failed: ${error.message}`;
      }
    }

    summary.push(row);
  });

  await visitUrl(page, target.url, options.waitMs);
  const linkedPages = await discoverLinkedPages(page, target.url, options.maxLinkedPages);
  for (const linkedUrl of linkedPages) {
    await visitUrl(page, linkedUrl, options.waitMs).catch((error) => {
      console.warn(`Failed to open linked page ${linkedUrl}: ${error.message}`);
    });
  }

  const sortedSummary = summary.toSorted((a, b) => b.candidateScore - a.candidateScore);
  const csv = [
    ["url", "status", "content_type", "response_size", "matched_keys", "candidate_score"]
      .map(csvEscape)
      .join(","),
    ...sortedSummary.map((row) =>
      [
        row.url,
        row.status,
        row.contentType,
        row.responseSize,
        row.matchedKeys.join("|"),
        row.candidateScore,
      ]
        .map(csvEscape)
        .join(","),
    ),
  ].join("\n");

  await writeFile(path.join(outputDir, "summary.csv"), `${csv}\n`);

  const candidates = [];
  const printedCandidateUrls = new Set();
  for (const row of sortedSummary) {
    if (row.candidateScore <= 0 || printedCandidateUrls.has(row.url)) {
      continue;
    }
    printedCandidateUrls.add(row.url);
    candidates.push(row);
  }
  console.log(`\nCandidate endpoints for ${target.sourceId}:`);
  if (candidates.length === 0) {
    console.log("  none found");
  } else {
    for (const row of candidates) {
      console.log(
        `  score=${row.candidateScore} status=${row.status} keys=${row.matchedKeys.join("|")} ${row.url}`,
      );
    }
  }
  console.log(`Saved ${savedUrls.size} JSON responses and ${summary.length} summary rows to ${outputDir}`);

  await context.close();
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const targets = options.targets.length > 0 ? options.targets : DEFAULT_TARGETS;
  const browser = await chromium.launch({ headless: !options.headed });
  try {
    for (const target of targets) {
      await runTarget(browser, target, options);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
