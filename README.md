# Generator obrazu e-paper

Prosta aplikacja desktopowa do przygotowywania obrazów i surowych plików BIN dla monochromatycznego wyświetlacza e-paper 800 × 480 px.

Wymagany jest Python 3.9 lub nowszy.

## Funkcje

- wybór obrazu PNG, JPG, WEBP, BMP lub TIFF,
- podgląd źródła i finalnego obrazu 1-bitowego,
- tryby: Dopasuj, Wypełnij i Rozciągnij,
- regulowany próg czerni i bieli 0–255,
- opcjonalne odwrócenie kolorów,
- zapis podglądu PNG i framebufferu BIN,
- kontrola wymiarów 800 × 480 i rozmiaru BIN 48 000 B.
- wysyłanie PNG i BIN na serwer przez SCP z użyciem klucza SSH.

## Instalacja

```bash
cd "/Users/konrad/Desktop/Smart Home/dashboard_generator"
/opt/homebrew/bin/python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Tkinter na macOS z Homebrew

Na aktualnym macOS nie używaj systemowego Pythona 3.9, ponieważ jest połączony z przestarzałym Tk 8.5 i może wyświetlać puste okno. Zainstaluj wersję Homebrew:

```bash
brew install python@3.14
brew install python-tk@3.14
```

Po aktywowaniu środowiska możesz sprawdzić wersje:

```bash
python --version
python -c 'import tkinter as tk; root=tk.Tk(); print(root.tk.call("info", "patchlevel")); root.destroy()'
```

Zalecany jest Python 3.14 oraz Tk 9.x lub co najmniej Tk 8.6.

## Uruchomienie

```bash
python app.py
```

## Aplikacja macOS

Pakiet `.app` możesz zbudować jednorazowo przez PyInstaller:

```bash
source .venv/bin/activate
pip install -r requirements-build.txt
./build_app.sh
```

Gotowa aplikacja powstanie jako:

```text
dist/Dashboard Generator.app
```

Ikona aplikacji jest przechowywana w `assets/app-icon.icns`. Jej źródłowa wersja PNG znajduje się w `assets/app-icon.png`.

Możesz ją uruchamiać z Findera albo przeciągnąć do katalogu `/Applications`. Do codziennego używania nie jest potrzebny terminal ani aktywowanie środowiska `.venv`.

Pakiet jest przeznaczony do lokalnego użytku i nie jest podpisany certyfikatem Apple. Jeśli macOS zablokuje pierwsze uruchomienie, kliknij aplikację prawym przyciskiem i wybierz **Otwórz**, a następnie potwierdź uruchomienie.

## Testy

```bash
python -m unittest discover -s tests
```

## Tryby dopasowania

- **Dopasuj** — pokazuje cały obraz i dodaje białe marginesy, jeśli proporcje są inne.
- **Wypełnij** — wypełnia ekran i centralnie przycina nadmiar.
- **Rozciągnij** — wymusza dokładnie 800 × 480 px bez zachowania proporcji.

W każdym trybie wynik końcowy ma 800 × 480 px i jest zapisywany jako jednobitowy framebuffer o rozmiarze 48 000 bajtów.

## Wysyłanie na serwer

Po wybraniu obrazu i przygotowaniu poprawnego podglądu aktywuje się przycisk **Wyślij na serwer**. Nie trzeba wcześniej zapisywać plików lokalnie. Aplikacja tworzy pliki tymczasowe, bez dodatkowego potwierdzenia nadpisuje:

```text
zuczek@192.168.100.121:/home/zuczek/dashboard/output/nightmode.bin
zuczek@192.168.100.121:/home/zuczek/dashboard/output/nightmode.png
```

Wysyłanie korzysta z `scp`, portu 22 oraz istniejącego klucza SSH. Hasło ani klucz prywatny nie są przechowywane w aplikacji.
