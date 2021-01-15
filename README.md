# industry2

Python 3.8.2

## Installation

- `pip install -r requirements.txt`

### Requirements

- Serwer XMPP obsługujący autorejestrację (np. Prosody)

## Usage

- `python factory_gui.py`

## Links

- [Managing Multiple Python Versions With pyenv](https://realpython.com/intro-to-pyenv/)


## Todo

- [ ] abstrakcja modeli negocjacji + 
- [ ] dodać awarie, że sie mogą psuć
- [ ] różne strategie i w ogóle żeby współpracowały (proszenie o pomoc, udzielanie pomocy)
- [ ] MENADŻER (zrobić raz a dobrze i nie tykać):
    - [ ] żeby menedżer umiał ogarnąć awarię
    - [ ] menedżer ma lepiej przydzielać taski (zależnie od tego czy gom jest zajęty czy nie)
    - [ ] jeśli menadzer nie może przydzielić zadania, to niech się zatrzyma, a nie że spamuje
- [ ] FABRYKA:
    - [x] fabryka generuje zróżnicowane zamówienia
    - [ ] na gui reprezentować współpracujące try (jest lider [ten który ma zamówienie u TRa], zbierają się i wtedy zaczynają współpracę)
    - [x] Zoom jako pole w settings
    - [ ] Więcej informacji o GOM/TR po kliknięciu
    - [x] Jakiś viewmodel czy coś
    - [ ] tr_list deepcopy
    - [x] TickerBehav do apdejtowania wszystkich pozycji naraz
    - [ ] Hover
