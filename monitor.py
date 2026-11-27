import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Términos específicos de tu categoría
CLAVES_TCAE = [
    "tcae",
    "cuidados auxiliares de enfermería",
    "cuidados auxiliares de enfermeria",
    "auxiliar de enfermería",
    "auxiliar de enfermeria",
    "auxiliares de enfermería",
    "auxiliares de enfermeria",
    "grupo c1",
    "subgrupo c1",
    "reclasificación"
]

# Condiciones laborales, sueldo, jornada, mesa sectorial y OPE
CLAVES_LABORALES_Y_SUELDO = [
    "retribuciones", "tablas retributivas", "complemento específico",
    "complemento de destino", "complemento de carrera", "atención continuada",
    "turnicidad", "nocturnidad", "festivos", "guardias", "productividad",
    "pagas extraordinarias", "carrera profesional", "desarrollo profesional",
    "jornada", "35 horas", "cómputo anual", "horas", "vacaciones",
    "permisos", "licencias", "asuntos propios", "libre disposición",
    "días adicionales", "concurso de traslados", "traslados", "movilidad",
    "acoplamiento", "mesa sectorial", "estatuto marco",
    "oferta de empleo público", "ope"
]

# Contexto sanitario / estatutario
CONTEXTO_SANIDAD = [
    "estatutario", "estatutaria", "estatutarios", "estatutarias",
    "sanidad", "sanitat", "instituciones sanitarias",
    "sistema nacional de salud", "conselleria", "generalitat",
    "servicios de salud", "ingesa"
]

# Fuentes RSS de sindicatos (puedes añadir aquí cualquier URL /feed/ de otro sindicato)
FEEDS_SINDICATOS = {
    "CSIF Sanidad CV": "https://www.csif.es/es/rss/comunidad-valenciana/sanidad",
    "FSS-CCOO PV": "https://sanidad.ccoo.es/rss/pv",
    "SATSE CV": "https://www.satse.es/comunidad-valenciana/rss",
    "SAE Estatal": "https://www.sindicatosae.com/feed/"
}

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ARCHIVO_HISTORIAL = "vistos.txt"


def cargar_vistos():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return set()
    with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_vistos(vistos):
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        for item in sorted(vistos):
            f.write(item + "\n")


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    for i in range(0, len(mensaje), 4000):
        resp = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mensaje[i:i + 4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=20
        )
        resp.raise_for_status()


def es_relevante(texto, exigir_contexto=True):
    t = texto.lower()
    if any(p in t for p in CLAVES_TCAE):
        return True
    if any(c in t for c in CLAVES_LABORALES_Y_SUELDO):
        if not exigir_contexto or any(s in t for s in CONTEXTO_SANIDAD):
            return True
    return False


def revisar_boe(fecha_str, vistos):
    url_sumario = f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}"
    resp = requests.get(url_sumario, headers={"Accept": "application/xml"}, timeout=20)
    if resp.status_code != 200:
        return []

    resultados = []
    root = ET.fromstring(resp.content)
    for item in root.findall(".//item"):
        titulo = (item.findtext("titulo") or "").strip()
        url_pdf = (item.findtext("url_pdf") or "").strip()
        enlace = f"https://www.boe.es{url_pdf}" if url_pdf.startswith("/") else (url_pdf or "https://www.boe.es")
        if enlace in vistos:
            continue
        if es_relevante(titulo, exigir_contexto=True):
            vistos.add(enlace)
            resultados.append(f"🇪🇸 <b>BOE</b>: {titulo}\n🔗 {enlace}")
    return resultados


def revisar_dogv(fecha_iso, vistos):
    resultados = []
    consultas = [
        "tcae", "auxiliar de enfermería", "personal estatutario",
        "retribuciones", "carrera profesional", "jornada",
        "vacaciones", "permisos", "traslados", "mesa sectorial",
        "grupo c1", "oferta de empleo público"
    ]
    for q in consultas:
        url = "https://dogv.gva.es/datosabiertos/api/v1/disposiciones"
        params = {"texto": q, "fechaDesde": fecha_iso}
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("items") if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for doc in items:
                if not isinstance(doc, dict):
                    continue
                titulo = (doc.get("titulo") or doc.get("title") or "Publicación en DOGV").strip()
                enlace = (doc.get("url") or doc.get("urlPdf") or doc.get("enlace") or "https://dogv.gva.es").strip()
                if enlace.startswith("/"):
                    enlace = f"https://dogv.gva.es{enlace}"
                if enlace in vistos:
                    continue
                if es_relevante(titulo, exigir_contexto=True) or "sanitat" in titulo.lower() or "sanidad" in titulo.lower():
                    vistos.add(enlace)
                    resultados.append(f"🏥 <b>DOGV (Conselleria de Sanitat)</b>: {titulo}\n🔗 {enlace}")
        except Exception:
            continue
    return resultados


def revisar_sindicatos(vistos):
    resultados = []
    # Cabeceras completas de navegador real para evitar bloqueos 403 en WordPress
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    otras_ccaa = [
        "andalucía", "andalucia", "madrid", "cataluña", "catalunya",
        "galicia", "murcia", "extremadura", "castilla", "aragón", "aragon",
        "asturias", "cantabria", "navarra", "rioja", "baleares", "canarias",
        "euskadi", "país vasco", "pais vasco", "ceuta", "melilla"
    ]

    for nombre, feed_url in FEEDS_SINDICATOS.items():
        try:
            resp = requests.get(feed_url, headers=headers, timeout=20)
            print(f"[{nombre}] Estado HTTP: {resp.status_code}")
            if resp.status_code != 200:
                continue

            contenido = resp.content.strip()
            root = ET.fromstring(contenido)

            # Busca tanto formato RSS (<item>) como Atom (<entry>)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            print(f"[{nombre}] Noticias encontradas en el feed: {len(items)}")

            for item in items[:15]:
                titulo = (
                    item.findtext("title")
                    or item.findtext("{http://www.w3.org/2005/Atom}title")
                    or ""
                ).strip()

                enlace = (item.findtext("link") or "").strip()
                if not enlace:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        enlace = (link_el.get("href") or "").strip()

                if not enlace or enlace in vistos:
                    continue

                if nombre == "SAE":
                    if not any(ccaa in titulo.lower() for ccaa in otras_ccaa):
                        vistos.add(enlace)
                        resultados.append(f"📢 <b>{nombre}</b>: {titulo}\n🔗 {enlace}")
                elif es_relevante(titulo, exigir_contexto=False):
                    vistos.add(enlace)
                    resultados.append(f"📢 <b>{nombre}</b>: {titulo}\n🔗 {enlace}")
        except Exception as e:
            print(f"[{nombre}] Error leyendo feed: {e}")
            continue

    return resultados


def main():
    ahora = datetime.now()
    vistos = cargar_vistos()

    hallazgos = (
        revisar_boe(ahora.strftime("%Y%m%d"), vistos)
        + revisar_dogv((ahora - timedelta(days=1)).strftime("%Y-%m-%d"), vistos)
        + revisar_sindicatos(vistos)
    )

    if hallazgos:
        cabecera = f"🩺 <b>Novedades TCAE / Sanitat ({ahora.strftime('%d/%m/%Y')}):</b>\n\n"
        enviar_telegram(cabecera + "\n\n".join(hallazgos))
        guardar_vistos(vistos)


if __name__ == "__main__":
    main()
