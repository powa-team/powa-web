from setuptools import find_packages, setup

__VERSION__ = None

with open("powa/__init__.py") as f:
    for line in f:
        if line.startswith("__VERSION__"):
            __VERSION__ = line.split("=")[1].replace('"', "").strip()


requires = ["tornado>=2.0", "psycopg2"]

setup(
    name="powa-web",
    version=__VERSION__,
    author="powa-team",
    license="Postgresql",
    packages=find_packages(),
    install_requires=requires,
    include_package_data=True,
    url="https://powa.readthedocs.io/",
    description="A User Interface for the PoWA project",
    long_description="See https://powa.readthedocs.io/",
    scripts=["powa-web"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: System Administrators",
        "Intended Audience :: End Users/Desktop",
        "License :: Other/Proprietary License",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Database :: Front-Ends",
    ],
    python_requires=">=3.6, <4",
)
