# industry2

Python 3.8.2

## Installation

- `pip install -r requirements.txt`

### Requirements

- Serwer XMPP obsługujący autorejestrację (np. Prosody)

## Usage

- `python -m industry2`

## Links

- [Managing Multiple Python Versions With pyenv](https://realpython.com/intro-to-pyenv/)
- [Spade FSM](https://spade-mas.readthedocs.io/en/latest/behaviours.html?highlight=state#finite-state-machine-behaviour)


## Todo

- [ ] abstrakcja modeli negocjacji + 
- [ ] dodać awarie, że sie mogą psuć
- [ ] różne strategie i w ogóle żeby współpracowały (proszenie o pomoc, udzielanie pomocy)
- [x] MENADŻER (zrobić raz a dobrze i nie tykać):
    - [x] żeby menedżer umiał ogarnąć awarię
    - [x] menedżer ma lepiej przydzielać taski (zależnie od tego czy gom jest zajęty czy nie)
    - [x] jeśli menadzer nie może przydzielić zadania, to niech się zatrzyma, a nie że spamuje
- [ ] FABRYKA:
    - [x] fabryka generuje zróżnicowane zamówienia
    - [x] na gui reprezentować współpracujące try (jest lider [ten który ma zamówienie u TRa], zbierają się i wtedy zaczynają współpracę)
    - [x] Zoom jako pole w settings
    - [x] Jakiś viewmodel czy coś
    - [x] TickerBehav do apdejtowania wszystkich pozycji naraz
    - [x] Więcej informacji o GOM/TR po kliknięciu
      - [x] `kliknięcie_handle`
      - [x] `tr_list` deepcopy

## Docs
W decide() strategia decyduje czy nic nie robiacy TR (w stanie 'idle') ma zostac Liderem ogarniajacym sprawe wlasnego
GoMa, czy Pracownikiem pomagajacym Liderowi ze slownika zadeklarowanych pomocy 'helping'. Zwraca True jezeli pozostaje
bezrobotny.

W decide() strategia decyduje czy nic nie robiacy TR (w stanie 'idle') ma zostac Liderem ogarniajacym sprawe wlasnego
GoMa, czy Pracownikiem pomagajacym Liderowi ze slownika zadeklarowanych pomocy 'helping'. Zwraca True jezeli pozostaje
bezrobotny.

Do reprezentacji stanów TRa korzystamy z FSM
