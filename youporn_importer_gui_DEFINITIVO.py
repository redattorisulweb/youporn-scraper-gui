import requests
from bs4 import BeautifulSoup
import csv
from typing import Callable, List, Dict

try:
    from openpyxl import Workbook
except Exception:
    Workbook = None  # type: ignore
import tkinter as tk
from tkinter import messagebox, simpledialog

def estrai_dati_youporn(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[ERRORE] Connessione fallita per {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    def get_meta(prop):
        tag = soup.find("meta", property=prop)
        return tag['content'] if tag else None

    titolo  = get_meta("og:title")
    thumb   = get_meta("og:image")
    embed_u = get_meta("og:video") or get_meta("og:video:url") or get_meta("og:video:secure_url")
    if not embed_u:
        video_tag = soup.find("video")
        embed_u = video_tag["src"] if video_tag and video_tag.get("src") else None
    embed_code = f'<iframe src="{embed_u}" frameborder="0" allowfullscreen></iframe>' if embed_u else None

    return {
        "titolo": titolo,
        "thumbnail_url": thumb,
        "embed_code": embed_code,
        "sorgente": url
    }

def estrai_info_da_categoria(url_cat, max_video=20):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url_cat, headers=headers, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    risultati = []
    cards = soup.select('div.video-box.pc.js_video-box')
    for card in cards[:max_video]:
        data = {
            'video_id':      card.get('data-video-id'),
            'uploader_id':   card.get('data-uploader-id'),
            'uploader_type': card.get('data-uploader-type'),
            'uploader_name': card.get('data-uploader-name'),
        }
        a_tag = card.select_one('a.js_video-box-url[href^="/watch/"]')
        data['video_page_url'] = 'https://www.youporn.com' + a_tag['href'] if a_tag else None

        img = card.select_one('img.thumb-image')
        if img:
            data['thumbnail_url']    = img.get('data-src') or img.get('src')
            data['video_direct_url'] = img.get('data-mediabook')

        span = card.select_one('a.video-title-text span')
        data['titolo'] = span.text.strip() if span else None

        dur = card.select_one('div.video-duration span')
        data['durata'] = dur.text.strip() if dur else None

        spans = card.select('div.info-views-container')[-1].select('span.info-views')
        data['views']  = spans[0].text.strip() if len(spans)>0 else None
        data['rating'] = spans[1].text.strip() if len(spans)>1 else None

        risultati.append(data)
    return risultati

def importa_da_categoria_csv(url_cat, output_csv="categoria_dettagliata.csv", max_video=20):
    lista = estrai_info_da_categoria(url_cat, max_video)
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'video_id','uploader_id','uploader_type','uploader_name',
            'titolo','video_page_url','thumbnail_url','video_direct_url',
            'durata','views','rating'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in lista:
            writer.writerow(item)
    print(f"[FINE] Estratti {len(lista)} video in {output_csv}")

def estrai_info_da_categoria_multi(url_cat: str, pages: int, progress: Callable[[str], None] | None = None) -> List[Dict]:
    risultati: List[Dict] = []
    base = url_cat.split('?')[0].rstrip('/')
    for p in range(1, pages + 1):
        page_url = url_cat if p == 1 else f"{base}?page={p}"
        if progress:
            progress(f"[INFO] Pagina {p}: {page_url}\n")
        page_ris = estrai_info_da_categoria(page_url)
        for idx, v in enumerate(page_ris, start=1):
            if progress:
                progress(f"  {idx}. {v.get('titolo')}\n")
        risultati.extend(page_ris)
    return risultati

def salva_excel(lista: List[Dict], output_file: str = "categoria_dettagliata.xlsx") -> None:
    if Workbook is None:
        raise RuntimeError("openpyxl non disponibile")
    wb = Workbook()
    ws = wb.active
    headers = [
        'video_id','uploader_id','uploader_type','uploader_name',
        'titolo','video_page_url','thumbnail_url','video_direct_url',
        'durata','views','rating'
    ]
    ws.append(headers)
    for item in lista:
        ws.append([item.get(h) for h in headers])
    wb.save(output_file)

def avvia_gui():
    root = tk.Tk()
    root.title("Importatore YouPorn")
    root.geometry("700x500")

    tk.Label(root, text="Incolla l'URL (video o category):").pack(pady=5)
    entry = tk.Entry(root, width=80)
    entry.pack(pady=5)

    # Area di output
    output = tk.Text(root, wrap='word')
    output.pack(expand=True, fill='both', padx=10, pady=10)

    # Funzione per singolo video
    def estrai_singolo():
        url = entry.get().strip()
        if not url:
            messagebox.showerror("Errore", "Inserisci un URL valido.")
            return
        output.delete(1.0, tk.END)
        dati = estrai_dati_youporn(url)
        if dati:
            output.insert(tk.END, "TITOLO:\n" + str(dati['titolo']) + "\n\n")
            output.insert(tk.END, "THUMBNAIL:\n" + str(dati['thumbnail_url']) + "\n\n")
            output.insert(tk.END, "EMBED CODE:\n" + str(dati['embed_code']) + "\n")
        else:
            output.insert(tk.END, "Errore durante l'estrazione.")

    # Funzione per categoria
    def importa_categoria_gui():
        url = entry.get().strip()
        if not url:
            messagebox.showerror("Errore", "Inserisci l'URL di una categoria.")
            return

        pagine = simpledialog.askinteger(
            "Numero pagine", "Quante pagine importare?",
            initialvalue=1, minvalue=1, maxvalue=20
        )
        if pagine is None:
            return

        output.delete(1.0, tk.END)

        def log(msg: str) -> None:
            output.insert(tk.END, msg)
            output.see(tk.END)
            root.update_idletasks()

        log(f"[INFO] Avvio estrazione da: {url}\n")
        lista = estrai_info_da_categoria_multi(url, pagine, progress=log)

        try:
            salva_excel(lista)
            log("[INFO] File Excel salvato in categoria_dettagliata.xlsx\n")
            messagebox.showinfo(
                "Importa",
                f"Salvati {len(lista)} video in categoria_dettagliata.xlsx"
            )
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare Excel: {e}")

    # Pulsanti
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Estrai Dati Video", command=estrai_singolo).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Importa Categoria", command=importa_categoria_gui).grid(row=0, column=1, padx=5)

    root.mainloop()
      # Pulsanticiccione

if __name__ == "__main__":
    avvia_gui()
