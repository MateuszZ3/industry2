from setuptools import setup

# Meta-data.
NAME = 'industry2'
DESCRIPTION = 'Industry 4.0 v2'
URL = 'https://github.com/MateuszZ3/industry2'
EMAIL = ''
AUTHOR = ''
REQUIRES_PYTHON = '>=3.8.2'
VERSION = '0.0.1'

# What packages are required for this module to be executed?
REQUIRED = [
    # 'requests', 'maya', 'records',
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

with open('README.md') as f:
    readme = f.read()

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=readme,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    license='MIT',
    packages=['industry2'],
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Natural Language :: English',
    ],
)
