from setuptools import setup, find_packages

setup(
    name="workshop",
    version="0.1.0",
    description="Persistent context tool for Claude Code",
    author="Claude & Zach",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "workshop=src.cli:main",
        ],
    },
    python_requires=">=3.8",
)
