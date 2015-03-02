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
    author='Dalibo',
    license='Postgresql',
    packages=find_packages(),
    install_requires=requires,
    include_package_data=True,
    url="http://dalibo.github.io/powa",
    description="A User Interface for the PoWA project",
    long_description="See http://dalibo.github.io/powa",
    scripts=['powa-web'],
    classifiers=[
    "Development Status :: 4 - Beta",
    "Intended Audience :: System Administrators",
    "License :: Other/Proprietary License",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Database :: Front-Ends"]
)
