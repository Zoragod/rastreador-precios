import os
import time
from datetime import datetime
from dotenv import load_dotenv

import db
import scraper
import notifier

load_dotenv()

MONEDA = "S/."

def ejecutar_rastreo_automatico():
    """
    Script autónomo para ejecutarse en segundo plano (Cron Job / GitHub Actions / Programador de tareas).
    Revisa todos los productos guardados en la base de datos, extrae precios y envía alertas
    por correo si alguno alcanza su precio objetivo sin necesidad de abrir el navegador.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Iniciando rastreo automático de precios...")

    # Asegurar que las tablas existan
    try:
        db.init_db()
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        return

    productos = db.obtener_resumen_productos()
    if not productos:
        print("ℹ️ No hay productos registrados en la base de datos.")
        return

    print(f"📦 Total de productos a revisar: {len(productos)}")

    smtp_listo = notifier.esta_configurado()
    if not smtp_listo:
        print("⚠️ Advertencia: Notificaciones SMTP no configuradas. No se podrán enviar correos.")

    actualizados = 0
    ofertas_detectadas = 0
    correos_enviados = 0

    for prod in productos:
        p_id = prod["id_producto"]
        nombre = prod["nombre"]
        tienda = prod["tienda"]
        url = prod["url_producto"]
        p_obj = float(prod["precio_objetivo"])
        ya_notificado = bool(prod.get("notificado"))

        print(f"\n🔍 Consultando: {nombre} ({tienda})...")
        res = scraper.extraer_precio(url)

        if res["precio"] is not None:
            nuevo_precio = res["precio"]
            db.registrar_precio(p_id, nuevo_precio)
            actualizados += 1
            print(f"   💵 Precio actual: {MONEDA} {nuevo_precio:.2f} (Objetivo: {MONEDA} {p_obj:.2f})")

            # Evaluar si está en oferta
            if nuevo_precio <= p_obj:
                ofertas_detectadas += 1
                print(f"   🎯 ¡OFERTA ALCANZADA!")

                if not ya_notificado:
                    if smtp_listo:
                        print("   📧 Enviando correo de alerta...")
                        ok, msj = notifier.enviar_alerta_oferta(
                            nombre_producto=nombre,
                            tienda=tienda,
                            url_producto=url,
                            precio_actual=nuevo_precio,
                            precio_objetivo=p_obj,
                            precio_minimo=float(prod["precio_minimo"]) if prod["precio_minimo"] else nuevo_precio,
                            moneda=MONEDA
                        )
                        if ok:
                            db.actualizar_estado_notificacion(p_id, True)
                            correos_enviados += 1
                            print("   ✅ Correo enviado exitosamente.")
                        else:
                            print(f"   ❌ Falló el envío de correo: {msj}")
                    else:
                        print("   ⚠️ Oferta detectada, pero SMTP no está configurado.")
                else:
                    print("   ℹ️ Ya se había notificado previamente de esta oferta (evitando spam).")
            else:
                # Si volvió a subir por encima de la meta, resetear bandera
                if ya_notificado:
                    db.actualizar_estado_notificacion(p_id, False)
                    print("   🔄 El precio volvió a subir, bandera de notificación restablecida.")
        else:
            print(f"   ⚠️ No se pudo extraer precio: {res['error']}")

        time.sleep(1)  # Pequeña pausa de cortesía entre consultas

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🏁 Rastreo finalizado.")
    print(f"   - Productos actualizados: {actualizados}")
    print(f"   - Ofertas activas: {ofertas_detectadas}")
    print(f"   - Correos enviados: {correos_enviados}\n")

if __name__ == "__main__":
    ejecutar_rastreo_automatico()
