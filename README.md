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

### Review z Trello :p
- (**Lider 1.**) Poszukuje chetnych do pomocy (-> request).
- (**Lider 2.**) Zbiera odpowiedzi i potwierdza zgode, zbyt wiele odpowiedzi zgody (<- agree | refuse, -> agree | refuse)?
- (**Lider 6.**) Ozajmia GoM, ze towar dostarczony, gdy wszyscy Pomocnicy dojada (-> inform).
- (**Lider 7.**) Staje sie bezrobotny, 'idle'.

### TODO z Trello :p
- (**Lider 3.**) Czeka, az wymagana liczba TR pomagajacych zglosi sie do celu zaladunku (<- inform).
- (**Lider 4.**) Oznajmia pomocnikom, ze towar jest juz zaladowany i moga jechac do celu (-> inform).
- (**Lider 5.**) Zbiera informacje od Pracownikow, ktorzy juz dojechali (<- inform).
- (**Helper 1.**) Oznajmia Lidera, ze dotarl do celu (-> inform).
- (**Helper 2.**) Rusza, gdy dostanie informacje od Lidera o zakonczonym zaladunku (<- inform).
- (**Helper 3.**) Oznajmia Lidera, ze dotarl na miejsce rozladunku (-> inform).
- (**Helper 4.**) Staje sie bezrobotny, 'idle'.

### Poza tym
- Wielki refactor (nazwy orderów, handlerów, połączenie ich z wiadomościami) named tuple, dataclassy
- Walidacja assercji
- Przynajmniej szczątkowa dokumentacja, żeby *otworzyć* ten projekt na innych 
- Logi z treściami wszystkich wiadomości
