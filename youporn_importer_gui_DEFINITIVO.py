import requests
from bs4 import BeautifulSoup
import csv
import pandas as pd
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

def export_to_excel(data, path):
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)

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
        n = simpledialog.askinteger("Numero video", "Quanti video importare?", initialvalue=10, minvalue=1, maxvalue=100)
        if n is None:
            return
        output.delete(1.0, tk.END)
        output.insert(tk.END, "[INFO] Avvio estrazione da: " + url + "\n")
        lista = estrai_info_da_categoria(url, n)
        for idx, v in enumerate(lista, start=1):
            line = (
                f"{idx}. {v['titolo']} | {v['thumbnail_url']} | {v['video_direct_url']} | "
                f"{v['durata']} | {v['views']} views | {v['rating']}\n"
            )
            output.insert(tk.END, line)
        export_to_excel(lista, "categoria_dettagliata.xlsx")
        messagebox.showinfo("Importa", f"Salvati {len(lista)} video in categoria_dettagliata.xlsx")

    # Pulsanti
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Estrai Dati Video", command=estrai_singolo).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Importa Categoria", command=importa_categoria_gui).grid(row=0, column=1, padx=5)

    root.mainloop()
      # Pulsanticiccione

if __name__ == "__main__":
    avvia_gui()
