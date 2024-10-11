# This file uses the following encoding : utf-8

from setuptools import setup

with open("README.md", "r") as file:
    long_description = file.read()

setup(
    name='PyBlade',
    packages=['pyblade'],
    version='0.1.0',
    license='MIT',
    description="PyBlade is a lightweight and efficient template engine for Python, inspired by Laravel's Blade syntax,"
                " designed primarily for use with Django. It simplifies template development by offering "
                "intuitive @-based directives.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Antares Mugisho',
    author_email='antaresmugisho@gmail.com',
    url='https://antaresmugisho.vercel.app/',
    keywords=['python', 'django', 'laravel', 'blade', 'template'],
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
