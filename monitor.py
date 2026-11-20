import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Términos que te afectan directamente como TCAE estatutario fijo
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

# Cambios en sueldo, jornada, horas, vacaciones, permisos, carrera o traslados
CLAVES_LABORALES_Y_SUELDO = [
    "retribuciones",
    "tablas retributivas",
    "complemento específico",
    "complemento especifico",
    "complemento de destino",
    "complemento de carrera",
    "atención continuada",
    "atencion continuada",
    "turnicidad",
    "nocturnidad",
    "festivos",
    "guardias",
    "productividad",
    "pagas extraordinarias",
    "carrera profesional",
    "desarrollo profesional",
    "jornada",
    "35 horas",
    "cómputo anual",
    "computo anual",
    "horas",
    "vacaciones",
    "permisos",
    "licencias",
    "asuntos propios",
    "libre disposición",
    "libre disposicion",
    "días adicionales",
    "dias adicionales",
    "concurso de traslados",
    "traslados",
    "movilidad",
    "acoplamiento",
    "mesa sectorial",
    "estatuto marco"
]

# Contexto sanitario / estatutario para evitar avisos de otros cuerpos no relacionados
CONTEXTO_SANIDAD = [
    "estatutario",
    "estatutaria",
    "estatutarios",
    "estatutarias",
    "sanidad",
    "sanitat",
    "instituciones sanitarias",
    "sistema nacional de salud",
    "conselleria",
    "generalitat",
    "servicios de salud",
    "ingesa"
]

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


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


def es_relevante(texto):
    t = texto.lower()
    if any(p in t for p in CLAVES_TCAE):
        return True
    if any(c in t for c in CLAVES_LABORALES_Y_SUELDO) and any(s in t for s in CONTEXTO_SANIDAD):
        return True
    return False


def revisar_boe(fecha_str):
    url_sumario = f"https://www.boe.es/datosabiertos/api/boe/sumario/{fecha_str}"
    resp = requests.get(url_sumario, headers={"Accept": "application/xml"}, timeout=20)
    if resp.status_code != 200:
        return []

    resultados = []
    root = ET.fromstring(resp.content)
    for item in root.findall(".//item"):
        titulo = (item.findtext("titulo") or "").strip()
        url_pdf = (item.findtext("url_pdf") or "").strip()
        if es_relevante(titulo):
            enlace = f"https://www.boe.es{url_pdf}" if url_pdf.startswith("/") else (url_pdf or "https://www.boe.es")
            resultados.append(f"🇪🇸 <b>BOE</b>: {titulo}\n🔗 {enlace}")
    return resultados


def revisar_dogv(fecha_iso):
    resultados = []
    consultas = [
        "tcae",
        "auxiliar de enfermería",
        "cuidados auxiliares de enfermería",
        "personal estatutario",
        "retribuciones",
        "carrera profesional",
        "jornada",
        "vacaciones",
        "permisos",
        "traslados",
        "mesa sectorial",
        "grupo c1"
    ]
    vistos = set()
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
                clave_unica = f"{titulo}|{enlace}"
                if clave_unica in vistos:
                    continue
                if es_relevante(titulo) or "sanitat" in titulo.lower() or "sanidad" in titulo.lower():
                    vistos.add(clave_unica)
                    resultados.append(f"🏥 <b>DOGV (Conselleria de Sanitat)</b>: {titulo}\n🔗 {enlace}")
        except Exception:
            continue
    return resultados


def main():
    ahora = datetime.now()
    fecha_boe = ahora.strftime("%Y%m%d")
    fecha_dogv = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")

    hallazgos = revisar_boe(fecha_boe) + revisar_dogv(fecha_dogv)
    if hallazgos:
        cabecera = f"🩺 <b>Novedades TCAE / Estatutario ({ahora.strftime('%d/%m/%Y')}):</b>\n\n"
        enviar_telegram(cabecera + "\n\n".join(hallazgos))


if __name__ == "__main__":
    main()
