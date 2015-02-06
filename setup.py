from setuptools import setup, find_packages

__VERSION__ = None

with open('powa/__init__.py') as f:
    for line in f:
        if line.startswith('__VERSION__'):
            __VERSION__ = line.split('=')[1].replace("'", '').strip()


requires = ['sqlalchemy', 'tornado', 'psycopg2'],

setup(
    name='powa-web',
    version=__VERSION__,
    author='Dalibo',
    license='Postgresql',
    packages=find_packages(),
    install_requires=requires,
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
    "Topic :: Database :: Front-Ends"],
    package_data={
        'powa': [
            'templates/*.html',
            'static/css/*',
            'static/js/powa.min-all.js',
            'static/js/config.js',
            'static/js/require.js',
            'static/img/**/*',
        ]
    }
)
