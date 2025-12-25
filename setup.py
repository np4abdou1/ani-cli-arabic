"""
Setup script for ani-cli-arabic
For backward compatibility with older pip versions
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the version from version.py
version_file = Path(__file__).parent / "src" / "version.py"
version = {}
with open(version_file) as f:
    exec(f.read(), version)

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="ani-cli-arabic",
    version=version.get("__version__", "1.3.0"),
    description="Terminal-based anime streaming with Arabic subtitles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="np4abdou1",
    url="https://github.com/np4abdou1/ani-cli-arabic",
    project_urls={
        "Bug Tracker": "https://github.com/np4abdou1/ani-cli-arabic/issues",
        "Documentation": "https://github.com/np4abdou1/ani-cli-arabic#readme",
        "Source Code": "https://github.com/np4abdou1/ani-cli-arabic",
    },
    packages=find_packages(),
    package_data={
        '': ['*.json', '*.db'],
        'database': ['*.db', '*.json'],
    },
    include_package_data=True,
    install_requires=[
        "rich>=13.0.0",
        "requests>=2.31.0",
        "pypresence>=4.3.0",
        "cryptography>=41.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "ani-cli-arabic=src.app:main",
            "ani-cli-ar=src.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Environment :: Console",
    ],
    keywords="anime streaming cli arabic subtitles terminal",
    license="MIT",
)
