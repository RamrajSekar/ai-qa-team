"""Check installed distributions, including transitive packages, during image build."""
import importlib.metadata
import re


def validate(names):
    normalized = {re.sub(r'[-_.]+', '-', name).lower() for name in names}
    if any(any(term in name for term in ('selenium', 'playwright', 'puppeteer'))
           or name in {'robotframework-browser', 'robotframework-seleniumlibrary'} for name in normalized):
        raise RuntimeError('PROHIBITED_RUNNER_DEPENDENCY')


if __name__ == '__main__':
    validate(d.metadata['Name'] for d in importlib.metadata.distributions())
