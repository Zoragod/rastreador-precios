import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, Any, Optional

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

def limpiar_precio(texto_precio: str) -> Optional[float]:
    """
    Extrae y convierte una cadena de texto de precio a float.
    Maneja símbolos de moneda (S/., S/, $, €, etc.), comas y puntos.
    """
    if not texto_precio:
        return None
        
    texto_limpio = texto_precio.strip().lower()
    
    if any(palabra in texto_limpio for palabra in ["free", "gratis", "gratuito"]):
        return 0.0

    coincidencia = re.search(r"(\d+(?:[.,]\d+)*)", texto_limpio)
    if not coincidencia:
        return None
        
    numero_str = coincidencia.group(1)
    
    if "," in numero_str and "." in numero_str:
        if numero_str.rfind(",") > numero_str.rfind("."):
            numero_str = numero_str.replace(".", "").replace(",", ".")
        else:
            numero_str = numero_str.replace(",", "")
    elif "," in numero_str:
        partes = numero_str.split(",")
        if len(partes[-1]) == 2:
            numero_str = numero_str.replace(",", ".")
        else:
            numero_str = numero_str.replace(",", "")
            
    try:
        return round(float(numero_str), 2)
    except ValueError:
        return None

def detectar_tienda(url: str) -> str:
    """Detecta el nombre de la tienda según el dominio de la URL."""
    dominio = urlparse(url).netloc.lower()
    if "toscrape.com" in dominio:
        return "Books to Scrape"
    elif "steampowered.com" in dominio or "steamcommunity.com" in dominio:
        return "Steam"
    elif "mercadolibre." in dominio:
        return "Mercado Libre"
    return "Otro"

def _scrapear_toscrape(soup: BeautifulSoup) -> Optional[float]:
    precio_tag = soup.select_one("p.price_color")
    if precio_tag:
        return limpiar_precio(precio_tag.get_text())
    return None

def _scrapear_steam(soup: BeautifulSoup) -> Optional[float]:
    meta_price = soup.select_one("meta[itemprop='price']")
    if meta_price and meta_price.get("content"):
        try:
            return float(meta_price["content"].replace(",", "."))
        except ValueError:
            pass

    descuento_tag = soup.select_one(".discount_final_price")
    if descuento_tag:
        precio = limpiar_precio(descuento_tag.get_text())
        if precio is not None:
            return precio

    compra_tag = soup.select_one(".game_purchase_price")
    if compra_tag:
        precio = limpiar_precio(compra_tag.get_text())
        if precio is not None:
            return precio

    precio_bloque = soup.select_one(".price")
    if precio_bloque:
        return limpiar_precio(precio_bloque.get_text())

    return None

def _scrapear_generico(soup: BeautifulSoup) -> Optional[float]:
    meta_itemprop = soup.select_one("meta[itemprop='price']")
    if meta_itemprop and meta_itemprop.get("content"):
        precio = limpiar_precio(meta_itemprop["content"])
        if precio is not None:
            return precio

    meta_og = soup.select_one("meta[property='product:price:amount']")
    if meta_og and meta_og.get("content"):
        precio = limpiar_precio(meta_og["content"])
        if precio is not None:
            return precio

    selectores_comunes = [
        ".price", ".product-price", ".precio", "#priceblock_ourprice",
        ".current-price", ".offer-price", ".sale-price"
    ]
    for sel in selectores_comunes:
        elem = soup.select_one(sel)
        if elem:
            precio = limpiar_precio(elem.get_text())
            if precio is not None:
                return precio

    return None

def extraer_precio(url: str, timeout: int = 15) -> Dict[str, Any]:
    tienda = detectar_tienda(url)
    resultado = {
        "precio": None,
        "tienda": tienda,
        "error": None,
        "url": url
    }

    # Detección temprana de tiendas con barrera anti-bot estricta
    if tienda == "Mercado Libre":
        resultado["error"] = (
            "Mercado Libre cuenta con protección anti-bot (Akamai Challenge) que bloquea el rastreo automatizado. "
            "Puedes registrar su precio manualmente en la sección inferior."
        )
        return resultado

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        resultado["error"] = f"Tiempo de espera agotado al conectar con {url}"
        return resultado
    except requests.exceptions.HTTPError as e:
        resultado["error"] = f"Error HTTP {response.status_code}: {e}"
        return resultado
    except requests.exceptions.RequestException as e:
        resultado["error"] = f"Error de red o conexión: {e}"
        return resultado
    except Exception as e:
        resultado["error"] = f"Error inesperado al solicitar URL: {e}"
        return resultado

    try:
        # Si la respuesta contiene retos anti-bot tipo Cloudflare o Akamai
        if "challenge" in response.text.lower() or "suspicious-traffic" in response.text.lower():
            resultado["error"] = "La tienda bloqueó la consulta con un reto anti-bot. Registra el precio manualmente."
            return resultado

        soup = BeautifulSoup(response.text, "html.parser")
        precio = None

        if tienda == "Books to Scrape":
            precio = _scrapear_toscrape(soup)
        elif tienda == "Steam":
            precio = _scrapear_steam(soup)

        if precio is None:
            precio = _scrapear_generico(soup)

        if precio is not None:
            resultado["precio"] = precio
        else:
            resultado["error"] = "No se pudo identificar el precio en la página web proporcionada."

    except Exception as e:
        resultado["error"] = f"Error al procesar el HTML de la página: {e}"

    return resultado
