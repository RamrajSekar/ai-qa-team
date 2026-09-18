const { test } = require('@playwright/test');

test.describe('nested group', () => {
    test.skip('nested javascript', async ({ page }) => {
        await page.goto('/nested');
    });
});

test.describe('second group', () => {
    test.only('nested javascript', async ({ page }) => {
        await page.goto('/focused');
    });
});
