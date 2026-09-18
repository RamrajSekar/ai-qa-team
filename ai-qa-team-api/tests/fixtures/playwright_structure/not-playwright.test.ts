function test(name: string, callback: () => void) {
    callback();
}

test('ordinary application test', () => {
    console.log('not Playwright');
});
