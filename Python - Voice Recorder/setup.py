"""Setup configuration for Voice Recorder Pro."""

from setuptools import setup, find_packages

setup(
    name="voice-recorder-pro",
    version="2.0.0-beta",
    description="A professional audio recording and editing application",
    author="Development Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pyside6>=6.5.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "google-auth>=2.25.0",
        "google-auth-oauthlib>=1.1.0",
        "google-auth-httplib2>=0.2.0",
        "google-api-python-client>=2.100.0",
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "numpy>=1.24.0",
        "scipy>=1.11.0",
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "voice-recorder=src.entrypoint:main",
        ],
    },
)
