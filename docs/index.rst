.. industry2 documentation master file, created by
   sphinx-quickstart on Sun Jul 11 18:07:13 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to industry2's documentation!
=====================================

.. include:: ../README.rst

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage
   explanations
   reference

TODO
----

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
