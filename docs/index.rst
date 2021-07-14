.. industry2 documentation master file, created by
   sphinx-quickstart on Sun Jul 11 18:07:13 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to industry2's documentation!
=====================================

This site covers industry2’s usage & API documentation. For basic info on what industry2 is, including its public
changelog & how the project is maintained, please see the
`main project website <https://github.com/MateuszZ3/industry2/>`_.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Getting started
---------------

*

Installation
------------

After cloning the repository and meeting the requirements, install the project by running:

.. code-block::

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Todo and playground
===================

.. function:: enumerate(sequence[, start=0])

   Return an iterator that yields tuples of an index and an item of the
   *sequence*. (And so on.)

This should reference :func:`enumerate`. Does it?

* [Spade FSM](https://spade-mas.readthedocs.io/en/latest/behaviours.html?highlight=state#finite-state-machine-behaviour)

* [ ] abstrakcja modeli negocjacji +
* [ ] dodać awarie, że sie mogą psuć
* [ ] różne strategie i w ogóle żeby współpracowały (proszenie o pomoc, udzielanie pomocy)
* [x] MENADŻER (zrobić raz a dobrze i nie tykać):
   * [x] żeby menedżer umiał ogarnąć awarię
   * [x] menedżer ma lepiej przydzielać taski (zależnie od tego czy gom jest zajęty czy nie)
   * [x] jeśli menadzer nie może przydzielić zadania, to niech się zatrzyma, a nie że spamuje
* [ ] FABRYKA:
   * [x] fabryka generuje zróżnicowane zamówienia
   * [x] na gui reprezentować współpracujące try (jest lider [ten który ma zamówienie u TRa], zbierają się i wtedy zaczynają współpracę)
   * [x] Zoom jako pole w settings
   * [x] Jakiś viewmodel czy coś
   * [x] TickerBehav do apdejtowania wszystkich pozycji naraz
   * [x] Więcej informacji o GOM/TR po kliknięciu
      * [x] kliknięcie_handle
      * [x] tr_list deepcopy

W decide() strategia decyduje czy nic nie robiacy TR (w stanie 'idle') ma zostac Liderem ogarniajacym sprawe wlasnego
GoMa, czy Pracownikiem pomagajacym Liderowi ze slownika zadeklarowanych pomocy 'helping'. Zwraca True jezeli pozostaje
bezrobotny.

W decide() strategia decyduje czy nic nie robiacy TR (w stanie 'idle') ma zostac Liderem ogarniajacym sprawe wlasnego
GoMa, czy Pracownikiem pomagajacym Liderowi ze slownika zadeklarowanych pomocy 'helping'. Zwraca True jezeli pozostaje
bezrobotny.

Do reprezentacji stanów TRa korzystamy z FSM.
