import html
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests

# Términos específicos de TCAE y subgrupo C1
MENCIONA_TCAE = [
    "tcae",
    "cuidados auxiliares de enfermería",
    "cuidados auxiliares de enfermeria",
    "auxiliar de enfermería",
    "auxiliar de enfermeria",
    "auxiliares de enfermería",
    "auxiliares de enfermeria",
    "cuidados auxiliares",
    "grupo c2",
    "subgrupo c2"
]

# Condiciones laborales, sueldo, jornada, mesa sectorial y OPE
CLAVES_LABORALES_Y_SUELDO = [
    "retribuciones", "tablas retributivas", "complemento específico",
    "complemento de destino", "complemento de carrera", "atención continuada",
    "turnicidad", "nocturnidad", "festivos", "guardias", "productividad",
    "pagas extraordinarias", "carrera profesional", "desarrollo profesional",
    "jornada", "35 horas", "cómputo anual", "vacaciones",
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

# Otras profesiones sanitarias o categorías que deben descartarse salvo mención expresa a TCAE / C1
OTRAS_PROFESIONES = [
    "fisioterapeuta", "fisioterapeutas", "fisioterapia",
    "matrona", "matronas",
    "enfermero", "enfermera", "enfermeros", "enfermeras", "enfermería", "enfermeria",
    "médico", "médica", "médicos", "médicas", "medico", "medica", "medicos", "medicas",
    "facultativo", "facultativos", "mir", "eir",
    "celador", "celadores", "pinche", "pinches",
    "farmacéutico", "farmacéutica", "farmacia",
    "odontólogo", "odontóloga", "odontologia", "odontología",
    "logopeda", "logopedas", "terapeuta ocupacional", "psicólogo", "psicóloga", "psicologia", "psicología",
    "técnico superior", "tecnico superior", "laboratorio", "radiodiagnóstico", "radiodiagnostico", "imagen para el diagnóstico"
]

# Materias ajenas al régimen estatutario / laboral en boletines oficiales
EXCLUIR_BOLETINES = [
    "subvención", "subvenciones", "ayudas", "beca", "becas",
    "contrato de servicios", "suministro de", "licitación", "adjudicación",
    "convenio colectivo"
]

# Comunidades, ciudades, servicios de salud y siglas de fuera de la Comunitat Valenciana
OTRAS_CCAA_Y_ZONAS = [
    "andalucía", "andalucia", "sevilla", "málaga", "malaga", "granada", "córdoba", "cordoba",
    "cádiz", "cadiz", "huelva", "jaén", "jaen", "almería", "almeria",
    "madrid", "cataluña", "catalunya", "barcelona", "girona", "tarragona", "lleida",
    "galicia", "a coruña", "coruña", "vigo", "lugo", "ourense", "pontevedra",
    "murcia", "extremadura", "badajoz", "cáceres", "caceres", "mérida", "merida",
    "castilla", "valladolid", "león", "leon", "salamanca", "burgos", "toledo", "albacete", "cuenca",
    "aragón", "aragon", "zaragoza", "huesca", "teruel",
    "asturias", "oviedo", "gijón", "gijon",
    "cantabria", "santander",
    "navarra", "pamplona",
    "rioja", "logroño",
    "baleares", "mallorca", "menorca", "ibiza", "eivissa", "palma",
    "canarias", "tenerife", "gran canaria", "lanzarote", "fuerteventura",
    "euskadi", "país vasco", "pais vasco", "bilbao", "bizkaia", "gipuzkoa", "donostia", "álava", "alava",
    "ceuta", "melilla",
    " sas ", "sermas", "sescam", "sergas", "ib-salut", "ibsalut", "osakidetza", "sacyl", "sespa", "scs"
]

# Rastreo exclusivo en webs oficiales de sindicatos (sin prensa ni radio)
FEEDS_SINDICATOS = {
    "SAE": "https://news.google.com/rss/search?q=site:sindicatosae.com&hl=es&gl=ES&ceid=ES:es",
    "Sindicatos Oficiales": "https://news.google.com/rss/search?q=(site:csif.es+OR+site:satse.es+OR+site:sanidad.ccoo.es+OR+site:ugt-sp.es)+(Sanitat+OR+TCAE+OR+%22Mesa+Sectorial%22+OR+%22personal+estatutario%22+OR+%22Comunitat+Valenciana%22+OR+Valencia+OR+Alicante+OR+Castell%C3%B3n)&hl=es&gl=ES&ceid=ES:es"
}

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ARCHIVO_HISTORIAL = "vistos.txt"

HEADERS_NAVEGADOR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}


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


def es_tcae_o_comun_valido(texto, exigir_contexto=True, es_boletin=False):
    t = f" {texto.lower()} "
    es_tcae_expreso = any(p in t for p in MENCIONA_TCAE)

    if not es_tcae_expreso and any(prof in t for prof in OTRAS_PROFESIONES):
        return False

    if es_boletin and not es_tcae_expreso and any(ex in t for ex in EXCLUIR_BOLETINES):
        return False

    if es_tcae_expreso:
        return True

    if any(c in t for c in CLAVES_LABORALES_Y_SUELDO):
        if not exigir_contexto or any(s in t for s in CONTEXTO_SANIDAD):
            return True

    return False


def revisar_boe(fecha_str, vistos):
    url_sumario = f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}"
    headers = {
        "Accept": "application/xml",
        "User-Agent": HEADERS_NAVEGADOR["User-Agent"]
    }

    resp = None
    for intento in range(2):
        try:
            resp = requests.get(url_sumario, headers=headers, timeout=20)
            break
        except requests.exceptions.RequestException as e:
            print(f"[BOE {fecha_str}] Intento {intento + 1} fallido: {e}")

    if resp is None or resp.status_code != 200:
        return []

    resultados = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[BOE {fecha_str}] Error al leer XML: {e}")
        return []

    for item in root.findall(".//item"):
        titulo_raw = (item.findtext("titulo") or "").strip()
        url_pdf = (item.findtext("url_pdf") or "").strip()
        enlace = f"https://www.boe.es{url_pdf}" if url_pdf.startswith("/") else (url_pdf or "https://www.boe.es")
        if not enlace or enlace in vistos:
            continue
        if es_tcae_o_comun_valido(titulo_raw, exigir_contexto=True, es_boletin=True):
            vistos.add(enlace)
            resultados.append(f"🇪🇸 <b>BOE</b>: {html.escape(titulo_raw)}\n🔗 {enlace}")
    return resultados


def revisar_dogv(fecha_iso, vistos):
    resultados = []
    consultas = [
        "tcae", "auxiliar de enfermería", "personal estatutario",
        "retribuciones", "carrera profesional", "35 horas",
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
                titulo_raw = (doc.get("titulo") or doc.get("title") or "Publicación en DOGV").strip()
                enlace = (doc.get("url") or doc.get("urlPdf") or doc.get("enlace") or "https://dogv.gva.es").strip()
                if enlace.startswith("/"):
                    enlace = f"https://dogv.gva.es{enlace}"
                if not enlace or enlace in vistos:
                    continue
                if es_tcae_o_comun_valido(titulo_raw, exigir_contexto=True, es_boletin=True):
                    vistos.add(enlace)
                    resultados.append(f"🏥 <b>DOGV (Conselleria de Sanitat)</b>: {html.escape(titulo_raw)}\n🔗 {enlace}")
        except Exception:
            continue
    return resultados


def revisar_sindicatos(vistos):
    resultados = []

    for nombre, feed_url in FEEDS_SINDICATOS.items():
        try:
            resp = requests.get(feed_url, headers=HEADERS_NAVEGADOR, timeout=20)
            print(f"[{nombre}] Estado HTTP: {resp.status_code}")
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content.strip())
            items = root.findall(".//item")
            print(f"[{nombre}] Publicaciones encontradas: {len(items)}")

            for item in items[:15]:
                titulo_raw = (item.findtext("title") or "").strip()
                enlace = (item.findtext("link") or "").strip()
                if not enlace or enlace in vistos:
                    continue

                t_check = f" {titulo_raw.lower()} "

                if any(zona in t_check for zona in OTRAS_CCAA_Y_ZONAS):
                    continue

                es_tcae_expreso = any(p in t_check for p in MENCIONA_TCAE)
                if not es_tcae_expreso and any(prof in t_check for prof in OTRAS_PROFESIONES):
                    continue

                if nombre == "SAE":
                    vistos.add(enlace)
                    resultados.append(f"📢 <b>Web SAE</b>: {html.escape(titulo_raw)}\n🔗 {enlace}")
                elif es_tcae_o_comun_valido(titulo_raw, exigir_contexto=False, es_boletin=False):
                    vistos.add(enlace)
                    resultados.append(f"📢 <b>Web Sindical</b>: {html.escape(titulo_raw)}\n🔗 {enlace}")

        except Exception as e:
            print(f"[{nombre}] Error leyendo feed: {e}")
            continue

    return resultados


def main():
    ahora = datetime.now()
    vistos = cargar_vistos()

    hallazgos_boe = []
    for dias_atras in range(3):
        fecha_boe = (ahora - timedelta(days=dias_atras)).strftime("%Y%m%d")
        hallazgos_boe.extend(revisar_boe(fecha_boe, vistos))

    hallazgos = (
        hallazgos_boe
        + revisar_dogv((ahora - timedelta(days=3)).strftime("%Y-%m-%d"), vistos)
        + revisar_sindicatos(vistos)
    )

    if hallazgos:
        cabecera = f"🩺 <b>Novedades TCAE / Sanitat ({ahora.strftime('%d/%m/%Y')}):</b>\n\n"
        enviar_telegram(cabecera + "\n\n".join(hallazgos))
        guardar_vistos(vistos)


if __name__ == "__main__":
    main()
