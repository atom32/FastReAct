"""
FastReAct安装配置

注意：版本号从 src/fastreact/__init__.py 动态读取
"""

import re
from setuptools import setup, find_packages

def get_version():
    """从 __init__.py 读取版本号"""
    with open("src/fastreact/__init__.py", "r", encoding="utf-8") as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fastreact",
    version=get_version(),  # 动态读取版本
    author="FastReAct Team",
    author_email="contact@fastreact.dev",
    description="企业级 ReAct Agent 基础设施框架 - 开箱即用，生产就绪",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/atom32/FastReAct",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.0.0",
        "httpx>=0.25.0",
        "pydantic>=2.0.0",
        "click>=8.0.0",
        "mcp>=1.25.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "prompt-toolkit>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fastreact=fastreact.cli.main:cli",  # 统一使用 cli
        ],
    },
)
