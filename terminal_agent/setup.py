from setuptools import setup, find_namespace_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="terminal_agent",
    version="0.1.0",
    author="Emre Ozturk",
    author_email="iamrecan@gmail.com",
    description="A powerful terminal-based assistant with voice, calendar, and AI capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iamrecan/terminAI",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "terminal-agent=terminal_agent.core.agent:main",
        ],
    },
)
