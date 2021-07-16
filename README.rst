industry2
=========

**industry2** is a multi-agent system aiming to provide a platform to develop and test negotiation models between
*Transport Robots* in an `Industry 4.0 <https://www.ibm.com/topics/industry-4-0>`_ setting. Thanks for checking it out.

Goals
-----

The aim of this project is to explore the utilisation of a multi-agent system to model complex production processes in
a smart, automated factory with a focus on the transport of raw material and intermediate goods between *Groups of Ultra
Modern Machines* (GoM's) by autonomous *Transport Robots* (TR) assigned to each of them.

By design *Transport Robots* need to cooperate to complete orders issued by their *GoMs*. This in turn entails a
need to negotiate the order of completing orders. This functionality is implemented using a multi-agent
system which enables a consistent cooperation of all the *TRs* on the premises of the workplace, ensures a constant flow
of goods according to respective priorities, and handles emergency situations.

Getting started
---------------

*

Check out the :doc:`usage` section for further information.

Installation
------------

After cloning the repository and meeting the requirements, install the project by running:

.. code-block:: console

   $ pip install -r requirements.txt

in the project's root folder.

Requirements
^^^^^^^^^^^^

* Python (>= 3.8.2)
* A running XMPP server with auto-registration support (we recommend `Prosody <https://prosody.im/>`_).

Documentation
-------------

TODO: readthedocs

Local documentation
^^^^^^^^^^^^^^^^^^

To build the docs locally on your machine, first you will need to install the dependencies:

.. code-block:: console

   $ cd docs                          # change directory to the docs folder
   $ pip install -r requirements.txt  # Install docs dependencies

When the installation is succesful, run the following to build the HTML documentation:

.. code-block:: console

   $ make html

If the build is succesful, you will see a message:

.. code-block::
   
   ...
   build succedeed.
   
   The HTML pages are in _build/html.
   
Now you can access the index site (``/docs/_build/html/index.html``).

Contribute
----------

* Issue Tracker: https://github.com/MateuszZ3/industry2/issues
* Source Code: https://github.com/MateuszZ3/industry2

Support
-------

If you are having issues, please let us know, preferrably at: *tomulewicz.s [at] pm [dot] me*

License
-------

The project is licensed under the MIT license.
