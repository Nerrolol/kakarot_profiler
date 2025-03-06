from setuptools import setup, find_packages

setup(
    name="kakarot_profiler",
    version="0.1.0",
    description="Outil de profilage pour Kakarot",
    author="nerrolol",
    packages=find_packages(),
    install_requires=[
        "Flask", 
    ],
    entry_points={
        "console_scripts": [
            "kakarot-profiler=kakarot_profiler.cli:main",
        ],
    },
)
