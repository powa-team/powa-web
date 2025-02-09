**How to contribute to powa-web**

This documentation describes how to set up an environment for powa-web or how
to maintain it.

This project relies on a few frameworks / libraries including:

 - VueJS,
 - Vuetify,
 - D3,
 - ViteJS.

# Set up dev environment

For the following steps, we assume you use PoWA web in debug mode (for example
by running `./run-powa.py` or using podman dev environment).

### Python syntax and formatting

Python syntax and formatting must conform to ruff. CI checks new code with ruff.

If not already available, you can create a virtualenv for developpement purpose:

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

You can then do a syntax check and format check by running the following command:

``` shell
ruff check
ruff format --check --diff
```

## Requirements

 - A recent version of `NodeJS` (16+) and `npm` are required.

## Install JS packages

```shell
npm ci
```

It installs a clean version of the project by installing packages with versions
declared in the `package-lock.json` file.

## Serve files wih ViteJS

In a new terminal, execute:

```shell
npm run dev
```

It launches a `ViteJS` server running on 5173 port. It serves the JS and CSS
files dynamically, and in most cases modifications made on the files will be
taken into account directly without having to reload the page in the browser.

At this point, you should be able to use powa-web in your browser.

Beware that the first page load in the browser may take some time. ViteJS needs
to build dependencies at first launch.

# JS/CSS libraries maintenance

## Audit the package vulnerabilities

Using `npm audit` you can check if packages powa depends on are vulnerable. If
it reports high severity vulnerabilities, it is recommended to update the
involved packages either using `npm audit fix` or `npm install
name-of-package`.

## Update packages

To update libraries, you can run:

```
npm install name-of-package
```

This will take `package.json` settings into account and will only install
versions that match the one declared there if the package is already installed.

Please refer to https://docs.npmjs.com/about-semantic-versioning.

Don't forget to commit changes in both `package.json` and `package-lock.json`
if need be.

# Build for production

When PoWA runs in production mode, it relies on built assets. Those built
static assets can be found in `powa/static/dist`.

To build the assets from the current source files, run:

```shell
npm run build
```

This is to be done before releasing a new version. Don't forget to commit the
new static files that may have been created in `dist`.
