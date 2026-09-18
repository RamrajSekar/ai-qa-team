export class ExamplePage {
    constructor(private page: unknown) {}

    async open(path: string) {
        await this.navigate(path);
    }

    async navigate(path: string) {
        return path;
    }
}
