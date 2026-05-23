import { test, expect } from "@playwright/test";

test.describe("Smoke Tests", () => {
  test("homepage loads with title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/FileBRSR/i);
  });

  test("homepage has CTA button", async ({ page }) => {
    await page.goto("/");
    const cta = page.locator('a[href*="upload"], a[href*="signup"], button:has-text("Start")').first();
    await expect(cta).toBeVisible();
  });

  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("text=Sign in")).toBeVisible({ timeout: 10000 });
  });

  test("signup page renders", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.locator("text=Sign up")).toBeVisible({ timeout: 10000 });
  });

  test("pricing page renders", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.locator("text=Pricing")).toBeVisible({ timeout: 10000 });
  });

  test("upload page redirects to login for unauthenticated", async ({ page }) => {
    await page.goto("/upload");
    // Should redirect to login
    await page.waitForURL(/login|auth/, { timeout: 10000 });
  });
});

test.describe("API Health", () => {
  test("backend health check responds", async ({ request }) => {
    const baseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
    const resp = await request.get(`${baseUrl}/backend/health`);
    expect(resp.status()).toBe(200);
  });

  test("datapoints taxonomy available", async ({ request }) => {
    const baseUrl = process.env.E2E_BASE_URL || "http://localhost:3000";
    const resp = await request.get(`${baseUrl}/backend/api/v2/datapoints`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.total).toBeGreaterThan(300);
  });
});
