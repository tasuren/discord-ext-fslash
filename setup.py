# discord-ext-fslash - setup

from setuptools import setup
from os.path import exists


NAME = "discord-ext-fslash"
DESCRIPTION = "Force the discord.py command framework to correspond to the slashes."


if exists("README.md"):
    with open("README.md", "r") as f:
        long_description = f.read()
else:
    long_description = DESCRIPTION


with open(f"{NAME.replace('-', '/')}/__init__.py", "r") as f:
    text = f.read()
version = text.split('__version__ = "')[1].split('"')[0]
author = text.split('__author__ = "')[1].split('"')[0]


with open("requirements.txt", "r") as f:
    REQUIREMENTS = (f.read(),)


setup(
    name=NAME,
    version=version,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=f'https://github.com/tasuren/{NAME}',
    project_urls={
        "Documentation": f"https://tasuren.github.io/{NAME}"
    },
    author=author,
    author_email='tasuren@aol.com',
    license='MIT',
    keywords='discord discord.py',
    packages=["discord.ext.fslash"],
    install_requires=REQUIREMENTS,
    extras_requires={},
    python_requires='>=3.8.0',
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
    ]
)