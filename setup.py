from setuptools import setup, find_packages
import sys

__VERSION__ = None

with open('powa/__init__.py') as f:
    for line in f:
        if line.startswith('__VERSION__'):
            __VERSION__ = line.split('=')[1].replace("'", '').strip()


requires = [
    'sqlalchemy>=0.7.2',
    'tornado>=2.0',
    'psycopg2'
]

# include ordereddict for python2.6
if sys.version_info < (2, 7, 0):
    requires.append('ordereddict')


setup(
    name='powa-web',
    version=__VERSION__,
    author='powa-team',
    license='Postgresql',
    packages=find_packages(),
    install_requires=requires,
    include_package_data=True,
    url="https://powa.readthedocs.io/",
    description="A User Interface for the PoWA project",
    long_description="See https://powa.readthedocs.io/",
    scripts=['powa-web'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Intended Audience :: End Users/Desktop",
        "License :: Other/Proprietary License",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Database :: Front-Ends"]
)
