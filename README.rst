
.. image:: http://dalibo.github.io/powa/img/logo.png
    :alt: PoWA logo
    :align: center
    
PoWA UI
=======

This project is a UI to the PoWA project

Install
=======

Dependencies
------------

To run the UI, you will need:
  tornado
  sqlalchemy >= 0.7.8
  psycopg2

On debian:

  apt-get install python-tornado python-sqlalchemy python-psycopg2

Using pip:
  pip install -r requirements.txt

The UI needs to connect to a PostgreSQL database running PoWA.


Configuration
=============

Copy the powa.conf-dist as powa.conf. Modify the parameters to suit your actual
PostgreSQL server.

Running
=======

python run_powa.py

Deploying
=========

There are several options to deploy this application.

Apache
======

TODO

uWSGI
=====

TODO

Nginx on front of uWSGI
=======================

TODO
