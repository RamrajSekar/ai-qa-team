import { test, expect } from '@playwright/test';
import { importedHelper, duplicateHelper } from '../helpers/actions';
import { ExamplePage } from '../pages/ExamplePage';
import { missing } from '../../../../outside';

async function localHelper(value: string) {
    await importedHelper(value);
}

function recursiveHelper() {
    recursiveHelper();
}

test('basic structure', { tag: ['@structural', '@typescript'] }, async ({ page }) => {
    const variableValue = 'value';
    const month = '11';
    const year = '2026';
    const examplePage = new ExamplePage(page);
    await localHelper('literal value');
    await importedHelper(variableValue, process.env.TEST_USER, `${month}-${year}`);
    await duplicateHelper();
    await examplePage.open('/home');
    await page.goto('/dashboard');
    await expect(page.locator('.result')).toBeVisible();
    await unknownHelper();
    await handlers[methodName]();
    recursiveHelper();
});
