import { cycleA } from './cycle-a';

export async function importedHelper(page: unknown) {
    await cycleA();
}

export function duplicateHelper() {
    return 'first';
}

export function duplicateHelper() {
    return 'second';
}
