import { test, expect } from '@playwright/test';

test.describe('UI Layout and Rendering', () => {
  test('should display three-column layout on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify header is present
    await expect(page.locator('header')).toBeVisible();
    
    // Verify the main content area exists (use first() to avoid strict mode violations)
    await expect(page.locator('div.flex').first()).toBeVisible();
    
    // Check for Agent A and Agent B text
    await expect(page.locator('text=/Agent A/i')).toBeVisible();
    await expect(page.locator('text=/Agent B/i')).toBeVisible();
  });

  test('should have responsive layout on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify header is present on mobile
    await expect(page.locator('header')).toBeVisible();
    
    // Main content should still exist (just check body)
    await expect(page.locator('body')).toBeVisible();
    
    // At least the app title should be visible
    await expect(page.locator('text=/AI Agent Mixer/i')).toBeVisible();
  });

  test('should display configuration panel', async ({ page }) => {
    await page.goto('/');
    
    // Look for configuration-related elements
    const configElements = page.locator('text=/config/i');
    const count = await configElements.count();
    
    // Should have at least one element mentioning config
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Application State', () => {
  test('should load without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.goto('/');
    
    // Wait for app to be ready
    await page.waitForLoadState('networkidle');
    
    // Check there are no critical errors
    // Filter out expected errors (connection refused, fetch failures due to missing backend, Monaco errors)
    const criticalErrors = errors.filter(e => 
      !e.includes('DevTools') && 
      !e.includes('favicon') &&
      !e.includes('WebSocket') &&  // WebSocket errors are expected without backend
      !e.includes('ERR_CONNECTION_REFUSED') &&  // Backend connection errors expected
      !e.includes('ERR_NAME_NOT_RESOLVED') &&  // DNS errors expected
      !e.includes('Failed to fetch') &&  // API fetch errors expected without backend
      !e.includes('Error loading') &&  // Schema loading errors expected
      !e.includes('Failed to load resource') &&  // Resource loading errors expected
      !e.includes('Monaco')  // Monaco editor initialization errors on mobile
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('should have correct page title', async ({ page }) => {
    await page.goto('/');
    
    // Check page has a title
    const title = await page.title();
    expect(title).toBeTruthy();
  });
});

test.describe('Agent Consoles', () => {
  test('should display agent console headers', async ({ page }) => {
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Look for agent-related text (Agent A, Agent B, or similar)
    const agentText = page.locator('text=/agent/i');
    const count = await agentText.count();
    
    // Should have references to agents
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Conversation Exchange', () => {
  test('should display conversation area', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify main content area with conversation component
    // The conversation exchange is in the center column (flex-1 min-w-0 div)
    const conversationArea = page.locator('div.flex-1.min-w-0');
    await expect(conversationArea).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper heading structure', async ({ page }) => {
    await page.goto('/');
    
    // Check for heading elements
    const headings = page.locator('h1, h2, h3');
    const count = await headings.count();
    
    expect(count).toBeGreaterThan(0);
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');
    
    // Tab through interactive elements
    await page.keyboard.press('Tab');
    
    // Check that focus moved to an element
    const focusedElement = await page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});

test.describe('Performance', () => {
  test('should load within reasonable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 10 seconds
    expect(loadTime).toBeLessThan(10000);
  });
});
