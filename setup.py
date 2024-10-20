# This file uses the following encoding : utf-8

from setuptools import setup

with open("README.md", "r") as file:
    long_description = file.read()

setup(
    name="PyBlade",
    packages=["pyblade"],
    version="0.1.1",
    license="MIT",
    description="PyBlade is a powerful template engine for Python, initially designed for Django. Inspired by "
    "Laravel's Blade and Livewire, it simplifies dynamic template creation with developer-friendly "
    "@-based directives and component support, all while prioritizing security.",
    url="https://github.com/antaresmugisho/pyblade",
    download_url="https://github.com/antaresmugisho/pyblade/archive/refs/tags/v0.1.0-alpha.tar.gz",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Antares Mugisho",
    author_email="antaresmugisho@gmail.com",
    keywords=["python", "django", "laravel", "blade", "template"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",
        "Topic :: Text Processing :: Markup :: HTML",
        "Security :: Security",
    ],
)
