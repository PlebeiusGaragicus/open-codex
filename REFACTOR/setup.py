from setuptools import setup, find_packages

setup(
    name="open-codex",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=8.1.0',
        'python-dotenv>=1.0.0',
        'pyyaml>=6.0.0',
        'rich>=13.0.0',
        'httpx>=0.24.0',  # Async HTTP client
    ],
    extras_require={
        'test': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-mock>=3.12.0',
            'respx>=0.20.0',  # Mock HTTP responses
        ],
    },
    entry_points={
        'console_scripts': [
            'codex=src.cli.main:cli',
        ],
    },
)