from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import threading

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as error:
    if error.name == "_tkinter":
        print(
            "Brak modułu Tkinter dla używanej wersji Pythona.\n"
            "Na macOS z Pythonem 3.14 zainstaluj go poleceniem:\n\n"
            "    brew install python-tk@3.14\n"
        )
        sys.exit(1)
    raise

from PIL import Image, ImageTk

from converter import ConversionError, load_source_image, prepare_image, save_outputs
from settings import (
    DEFAULT_THRESHOLD,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    EXPECTED_BINARY_SIZE,
    FIT_CONTAIN,
    FIT_MODES,
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
)
from transfer import TransferError, upload_dashboard


class DashboardGeneratorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        tk_version_text = str(self.tk.call("info", "patchlevel"))
        tk_version = tuple(
            int(part)
            for part in tk_version_text.split(".")[:2]
        )
        if tk_version < (8, 6):
            self.withdraw()
            message = (
                f"Wykryto przestarzały Tk {tk_version_text}. "
                "Ta wersja nie wyświetla poprawnie interfejsu na aktualnym macOS.\n\n"
                "Utwórz środowisko przez Python Homebrew 3.14 zgodnie z README."
            )
            print(message)
            messagebox.showerror("Nieobsługiwana wersja Tk", message)
            self.destroy()
            raise SystemExit(1)

        self.title("Generator obrazu e-paper")
        self.minsize(1050, 650)
        self.geometry("1180x720")

        self.source_path: Path | None = None
        self.source_image: Image.Image | None = None
        self.output_image: Image.Image | None = None
        self.source_photo: ImageTk.PhotoImage | None = None
        self.output_photo: ImageTk.PhotoImage | None = None
        self.preview_job: str | None = None

        self.fit_mode = tk.StringVar(value=FIT_CONTAIN)
        self.threshold = tk.DoubleVar(value=DEFAULT_THRESHOLD)
        self.threshold_label = tk.StringVar(value=str(DEFAULT_THRESHOLD))
        self.invert = tk.BooleanVar(value=False)
        self.file_label = tk.StringVar(value="Nie wybrano pliku")
        self.status = tk.StringVar(value="Wybierz obraz, aby rozpocząć.")
        self.output_info = tk.StringVar(
            value=f"Docelowo: {DISPLAY_WIDTH} × {DISPLAY_HEIGHT} px · "
            f"1 bit · {EXPECTED_BINARY_SIZE:,} B".replace(",", " ")
        )

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Arial", 20, "bold"))
        style.configure("Section.TLabel", font=("Arial", 12, "bold"))
        style.configure("Status.TLabel", font=("Arial", 11))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(
            header,
            text="Generator obrazu e-paper",
            style="Title.TLabel",
        ).pack(side="left")
        ttk.Label(
            header,
            text="800 × 480 · 1 bit",
            style="Section.TLabel",
        ).pack(side="right")

        previews = ttk.Frame(root)
        previews.pack(fill="both", expand=True)
        previews.columnconfigure(0, weight=1)
        previews.columnconfigure(1, weight=1)
        previews.rowconfigure(1, weight=1)

        ttk.Label(
            previews,
            text="OBRAZ ŹRÓDŁOWY",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 7))
        ttk.Label(
            previews,
            text="PODGLĄD E-PAPER",
            style="Section.TLabel",
        ).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 7))

        self.source_panel = tk.Label(
            previews,
            text="Brak obrazu",
            bg="#202020",
            fg="#d0d0d0",
            width=60,
            height=18,
        )
        self.source_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        self.output_panel = tk.Label(
            previews,
            text="Podgląd pojawi się po wybraniu obrazu",
            bg="#202020",
            fg="#d0d0d0",
            width=60,
            height=18,
        )
        self.output_panel.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(8, 0),
        )

        controls = ttk.LabelFrame(root, text=" Ustawienia konwersji ", padding=14)
        controls.pack(fill="x", pady=(16, 10))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Plik:").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.file_label).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=10,
        )
        ttk.Button(
            controls,
            text="Wybierz obraz…",
            command=self.choose_image,
        ).grid(row=0, column=2, sticky="e")

        ttk.Label(controls, text="Dopasowanie:").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(12, 0),
        )
        fit_combo = ttk.Combobox(
            controls,
            textvariable=self.fit_mode,
            values=FIT_MODES,
            state="readonly",
            width=18,
        )
        fit_combo.grid(row=1, column=1, sticky="w", padx=10, pady=(12, 0))
        fit_combo.bind("<<ComboboxSelected>>", self.schedule_preview)

        threshold_frame = ttk.Frame(controls)
        threshold_frame.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(12, 0),
        )
        threshold_frame.columnconfigure(1, weight=1)
        ttk.Label(threshold_frame, text="Próg czerni i bieli:").grid(
            row=0,
            column=0,
            sticky="w",
        )
        threshold_scale = ttk.Scale(
            threshold_frame,
            from_=0,
            to=255,
            variable=self.threshold,
            command=self.on_threshold_change,
        )
        threshold_scale.grid(row=0, column=1, sticky="ew", padx=12)
        ttk.Label(
            threshold_frame,
            textvariable=self.threshold_label,
            width=4,
            anchor="e",
        ).grid(row=0, column=2)

        ttk.Checkbutton(
            controls,
            text="Odwróć kolory",
            variable=self.invert,
            command=self.schedule_preview,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))

        footer = ttk.Frame(root)
        footer.pack(fill="x")
        footer.columnconfigure(0, weight=1)

        ttk.Label(
            footer,
            textvariable=self.output_info,
            style="Status.TLabel",
        ).grid(row=0, column=0, sticky="w")

        self.save_button = ttk.Button(
            footer,
            text="Zapisz PNG i BIN…",
            command=self.save_files,
            state="disabled",
        )
        self.save_button.grid(row=0, column=1, rowspan=2, sticky="e")

        self.upload_button = ttk.Button(
            footer,
            text="Wyślij na serwer",
            command=self.start_upload,
            state="disabled",
        )
        self.upload_button.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(10, 0),
        )

        ttk.Label(
            footer,
            textvariable=self.status,
            style="Status.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))

    def choose_image(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="Wybierz obraz",
            filetypes=(
                ("Obrazy", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("Wszystkie pliki", "*.*"),
            ),
        )
        if not selected_path:
            return

        try:
            source_image = load_source_image(selected_path)
        except ConversionError as error:
            messagebox.showerror("Nie można otworzyć obrazu", str(error))
            return

        self.source_path = Path(selected_path)
        self.source_image = source_image
        self.file_label.set(str(self.source_path))
        self._show_image(self.source_image, self.source_panel, "source_photo")
        self.update_preview()

    def on_threshold_change(self, value: str) -> None:
        rounded_value = round(float(value))
        self.threshold.set(rounded_value)
        self.threshold_label.set(str(rounded_value))
        self.schedule_preview()

    def schedule_preview(self, _event: object | None = None) -> None:
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
        self.preview_job = self.after(80, self.update_preview)

    def update_preview(self) -> None:
        self.preview_job = None
        if self.source_image is None:
            return

        self.upload_button.configure(state="disabled")

        try:
            self.output_image = prepare_image(
                source_image=self.source_image,
                fit_mode=self.fit_mode.get(),
                threshold=round(self.threshold.get()),
                invert=self.invert.get(),
            )
        except ConversionError as error:
            self.output_image = None
            self.save_button.configure(state="disabled")
            self.status.set(f"Błąd: {error}")
            return

        self._show_image(self.output_image, self.output_panel, "output_photo")
        self.save_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.status.set(
            f"Gotowe do zapisu · {DISPLAY_WIDTH} × {DISPLAY_HEIGHT} px · "
            f"BIN {EXPECTED_BINARY_SIZE:,} B".replace(",", " ")
        )

    def _show_image(
        self,
        image: Image.Image,
        panel: tk.Label,
        attribute_name: str,
    ) -> None:
        preview = image.convert("RGB")
        preview.thumbnail(
            (PREVIEW_WIDTH, PREVIEW_HEIGHT),
            Image.Resampling.LANCZOS,
        )
        photo = ImageTk.PhotoImage(preview)
        setattr(self, attribute_name, photo)
        panel.configure(image=photo, text="")

    def save_files(self) -> None:
        if self.output_image is None or self.source_path is None:
            return

        output_directory = filedialog.askdirectory(
            title="Wybierz katalog dla PNG i BIN"
        )
        if not output_directory:
            return

        base_name = self.source_path.stem
        preview_path = Path(output_directory) / f"{base_name}_preview.png"
        binary_path = Path(output_directory) / f"{base_name}.bin"

        try:
            saved_preview, saved_binary = save_outputs(
                self.output_image,
                preview_path,
                binary_path,
            )
        except (ConversionError, OSError) as error:
            messagebox.showerror("Nie udało się zapisać plików", str(error))
            return

        self.status.set(
            f"Zapisano {saved_preview.name} i {saved_binary.name} "
            f"({saved_binary.stat().st_size:,} B)".replace(",", " ")
        )
        messagebox.showinfo(
            "Pliki zapisane",
            f"PNG:\n{saved_preview}\n\nBIN:\n{saved_binary}\n\n"
            f"Rozmiar BIN: {saved_binary.stat().st_size:,} B".replace(",", " "),
        )

    def start_upload(self) -> None:
        if self.output_image is None:
            return

        self.save_button.configure(state="disabled")
        self.upload_button.configure(state="disabled")
        self.status.set("Wysyłanie nightmode.bin i nightmode.png…")

        worker = threading.Thread(
            target=self._upload_worker,
            args=(self.output_image.copy(),),
            daemon=True,
        )
        worker.start()

    def _upload_worker(self, output_image: Image.Image) -> None:
        try:
            with tempfile.TemporaryDirectory(
                prefix="dashboard-generator-"
            ) as temporary_directory:
                directory = Path(temporary_directory)
                preview_path, binary_path = save_outputs(
                    output_image,
                    directory / "nightmode.png",
                    directory / "nightmode.bin",
                )
                upload_dashboard(preview_path, binary_path)
        except (ConversionError, TransferError, OSError) as error:
            self.after(0, self._upload_failed, str(error))
            return

        self.after(0, self._upload_succeeded)

    def _upload_failed(self, details: str) -> None:
        self.save_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.status.set("Wysyłanie nie powiodło się.")
        messagebox.showerror("Błąd wysyłania", details)

    def _upload_succeeded(self) -> None:
        self.save_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.status.set("Pliki nightmode.bin i nightmode.png wysłano na serwer.")


if __name__ == "__main__":
    DashboardGeneratorApp().mainloop()
