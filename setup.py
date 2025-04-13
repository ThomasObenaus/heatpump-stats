from setuptools import find_packages, setup

setup(
    name="heatpump_stats",
    version="0.1.0",
    description="A tool to fetch and analyze Viessmann heat pump data",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "PyViCare>=2.21.0",
        "python-dotenv>=1.0.0",
        "pandas>=1.5.0",
        "matplotlib>=3.6.0",
        "schedule>=1.1.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "heatpump-stats=heatpump_stats.cli:main",
        ],
    },
    python_requires=">=3.7",
)
