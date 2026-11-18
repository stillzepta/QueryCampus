from setuptools import setup, find_packages

setup(
    name="querycampus",
    version="1.0.0",
    description="QueryCampus: RAG-Based Virtual University Receptionist & Campus Concierge",
    author="QueryCampus Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "chromadb>=0.5.0",
        "streamlit>=1.35.0",
        "pypdf>=4.2.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.1",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "querycampus-eval=querycampus.evaluation.benchmark:main",
            "querycampus-ingest=querycampus.pipeline.ingestion:main",
        ],
    },
)
