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
need to negotiate the order of completing orders. **[Właśnie ta funkcjonalność ma zostać odwzorowana]** using a multi-agent
system which enables a consistent cooperation of all the *TRs* on the premises of the workplace, ensures a constant flow
of goods according to respective priorities, and handles emergency situations.

**[Projekt zostanie wykonany przy pomocy platformy Smart Python Agent Development Environment w wersji 3.1.4
(SPADE) w języku Python 3.8, w oparciu o protokół komunikacyjny XMPP. Platforma udostępnia bibliotekizawierające zarówno
bazowe klasy agentów, jak i klasy wiadomości zgodnychze standardem FIPA ACL oraz metody umożliwiające ich obsługę
wewnątrz kodu.]**

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

Contribute
----------

* Issue Tracker: https://github.com/MateuszZ3/industry2/issues
* Source Code: https://github.com/MateuszZ3/industry2

Support
-------

If you are having issues, please let us know.
We have a mailing list located at: project@google-groups.com

License
-------

The project is licensed under the MIT license.
