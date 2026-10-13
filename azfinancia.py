#!/usr/bin/env python3
"""
azfinancia.py — mini administrador de FinancIA en Azure.

Versión corta y adaptada del script_az.py de la cursada (~1422 líneas).
Incluye lo que FUNCIONA en nuestro entorno (ambiente express):
consultas de estado, tags, recursos, métricas y rollback de imagen.

Start/Stop y logs NO se pueden hacer por CLI en este entorno (verificado:
--min-replicas no frena la app; az containerapp logs show crashea). Por eso
los comandos 'frenar', 'prender' y 'logs' abren la página exacta del portal.

Uso:
  python3 azfinancia.py                    # sin argumentos = estado
  python3 azfinancia.py estado             # app + imagen + health en vivo
  python3 azfinancia.py tags               # versiones en el ACR (con commit)
  python3 azfinancia.py repos              # repositorios del ACR
  python3 azfinancia.py apps               # container apps del grupo
  python3 azfinancia.py recursos           # todos los recursos del grupo
  python3 azfinancia.py metricas [user] [pass]  # métricas de Hikari/JVM/HTTP (pide login)
  python3 azfinancia.py imagen <sha>       # rollback / apuntar a otra versión (confirma)
  python3 azfinancia.py url                # URL pública del backend
  python3 azfinancia.py logs               # abre el Log stream del portal
  python3 azfinancia.py frenar             # abre el portal para Stop
  python3 azfinancia.py prender            # abre el portal para Start
"""

import getpass
import json
import subprocess
import sys

# ── Recursos reales del proyecto (no son secretos) ────────────────────────
SUB = "14894dfa-95c3-4525-aa09-3766e96ec070"
TENANT = "b1eea3ae-be33-4355-a382-19c8ce58ee71"
RG = "rg-financia"
ACR = "crfinancia"
REPO = "financia-back"
APP = "financia-back"

OK, ERR, INFO = "✅", "✗", "•"


def az(*args):
    """Ejecuta az CLI y devuelve JSON. Si falla, corta con el error."""
    r = subprocess.run(["az", *args, "--subscription", SUB, "-o", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{ERR} az {' '.join(args)} falló:\n{r.stderr.strip()}")
        sys.exit(1)
    return json.loads(r.stdout)


def titulo(texto):
    print("\n" + "═" * 56)
    print(f"  {texto}")
    print("═" * 56)


def linea(clave, valor):
    print(f"  {INFO} {clave:<10} {valor}")


def datos_app():
    d = az("containerapp", "show", "-n", APP, "-g", RG)
    p = d["properties"]
    return {"estado": p["runningStatus"],
            "imagen": p["template"]["containers"][0]["image"],
            "url": p["configuration"]["ingress"]["fqdn"]}


def estado():
    d = datos_app()
    titulo("ESTADO DE LA APP")
    emoji = OK if d["estado"] == "Running" else "⏸"
    linea("App", APP)
    linea("Estado", f"{emoji} {d['estado']}")
    linea("Imagen", d["imagen"])
    linea("URL", f"https://{d['url']}")
    print()
    # Health en vivo (anónimo: solo status; detalles con token).
    # curl verifica el TLS contra el almacén de certificados del sistema.
    for path in ("/api/v1/health", "/actuator/health"):
        r = subprocess.run(
            ["curl", "-s", "-m", "10", "-w", "\n%{http_code}",
             f"https://{d['url']}{path}"],
            capture_output=True, text=True)
        if r.returncode == 0:
            body, _, code = r.stdout.rpartition("\n")
            mark = OK if code.strip() == "200" else ERR
            print(f"  {mark} {path:<18} HTTP {code.strip()}")
            print(f"      {body[:100]}")
        else:
            print(f"  {ERR} {path:<18} sin respuesta (¿app frenada?)")
    print()


def tags():
    tags = az("acr", "repository", "show-tags", "--name", ACR, "--repository", REPO)
    titulo(f"VERSIONES EN EL ACR ({ACR}/{REPO}) — {len(tags)} tags")
    for t in tags:
        # Cruzar cada tag con el mensaje del commit (si el repo está clonado)
        g = subprocess.run(["git", "log", "-1", "--format=%s", t],
                           capture_output=True, text=True)
        msg = g.stdout.strip()[:58] if g.returncode == 0 else ""
        print(f"  {INFO} {t}   {msg}")
    print()


def repos():
    titulo(f"REPOSITORIOS EN {ACR}")
    for repo in az("acr", "repository", "list", "--name", ACR):
        print(f"  {INFO} {repo}")
    print()


def apps():
    titulo(f"CONTAINER APPS EN {RG}")
    for a in az("containerapp", "list", "-g", RG):
        e = a["properties"].get("runningStatus", "?")
        emoji = OK if e == "Running" else "⏸"
        print(f"  {emoji} {a['name']:<20} {e}")
    print()


def recursos():
    titulo(f"RECURSOS EN {RG}")
    for res in az("resource", "list", "-g", RG):
        tipo = res["type"].split("/")[-1]
        print(f"  {INFO} {tipo:<24} {res['name']}")
    print()


def metricas(email=None, password=None):
    """Métricas protegidas: pide credenciales, hace login y consulta Actuator."""
    d = datos_app()
    if d["estado"] != "Running":
        print(f"{ERR} La app está {d['estado']} — prendela antes (python3 azfinancia.py prender)")
        sys.exit(1)
    email = email or input("Email: ")
    password = password or getpass.getpass("Password (no se muestra): ")

    # Login → JWT (mismo flujo que la app móvil)
    login = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         f"https://{d['url']}/api/v1/auth/login",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": email, "password": password})],
        capture_output=True, text=True)
    try:
        token = json.loads(login.stdout).get("token")
    except json.JSONDecodeError:
        token = None
    if not token:
        print(f"{ERR} Login fallido: {login.stdout[:120]}")
        sys.exit(1)

    def metrica(nombre):
        r = subprocess.run(
            ["curl", "-s", "-m", "15",
             "-H", f"Authorization: Bearer {token}",
             f"https://{d['url']}/actuator/metrics/{nombre}"],
            capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return None

    titulo("MÉTRICAS EN VIVO (Actuator)")
    consultas = [
        ("HikariCP activas", "hikaricp.connections.active"),
        ("HikariCP esperando", "hikaricp.connections.pending"),
        ("HikariCP máx", "hikaricp.connections.max"),
        ("JVM memoria usada", "jvm.memory.used"),
        ("JVM uptime", "process.uptime"),
        ("HTTP requests", "http.server.requests"),
    ]
    for etiqueta, nombre in consultas:
        m = metrica(nombre)
        if not m or not m.get("measurements"):
            print(f"  {INFO} {etiqueta:<18} (sin datos)")
            continue
        v = m["measurements"][0]["value"]
        if "memory" in nombre:
            v = f"{v / 1048576:.0f} MB"
        elif "uptime" in nombre:
            s = int(v)
            v = f"{s // 3600}h {(s % 3600) // 60}m {s % 60}s"
        else:
            v = f"{v:.2f}"
        print(f"  {INFO} {etiqueta:<18} {v}")
    print()


def imagen(sha):
    """Apuntar la app a otra versión del ACR (rollback o roll-forward)."""
    print(f"\n  La app pasará a usar: {ACR}.azurecr.io/{REPO}:{sha}")
    if input("  ¿Confirmás? [sí/no]: ").strip().lower() != "sí":
        print("  Cancelado.")
        return
    az("containerapp", "update", "-n", APP, "-g", RG,
       "--image", f"{ACR}.azurecr.io/{REPO}:{sha}")
    print(f"\n{OK} Update aplicado — esperá ~30 s y corré 'estado' para verificar.\n")


def url():
    print("https://" + datos_app()["url"])


def portal(hoja):
    """Abre la página exacta del portal para operaciones que no existen por CLI."""
    enlaces = {
        "overview": f"https://portal.azure.com/#@{TENANT}/resource/subscriptions/{SUB}"
                    f"/resourceGroups/{RG}/providers/Microsoft.App/containerApps/{APP}/overview",
        "logstream": f"https://portal.azure.com/#@{TENANT}/resource/subscriptions/{SUB}"
                     f"/resourceGroups/{RG}/providers/Microsoft.App/containerApps/{APP}/logStream",
    }
    subprocess.run(["open", enlaces[hoja]])
    print(f"\n  Se abrió el portal en la página correspondiente ({hoja}).")


def logs():
    print("\n  El CLI de esta versión no soporta logs en el ambiente express.")
    print("  Abriendo el Log stream del portal…")
    portal("logstream")


def frenar():
    print("\n  Stop no existe por CLI en este entorno (verificado: --min-replicas no aplica).")
    print("  Abriendo el portal para el botón Stop…")
    portal("overview")


def prender():
    print("\n  Start no existe por CLI en este entorno (verificado).")
    print("  Abriendo el portal para el botón Start…")
    portal("overview")


COMANDOS = {"estado": estado, "tags": tags, "repos": repos, "apps": apps,
            "recursos": recursos, "url": url, "logs": logs,
            "frenar": frenar, "prender": prender}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        estado()
    elif sys.argv[1] == "imagen":
        if len(sys.argv) < 3:
            print("Uso: python3 azfinancia.py imagen <sha>")
            sys.exit(1)
        imagen(sys.argv[2])
    elif sys.argv[1] == "metricas":
        metricas(*sys.argv[2:4])
    elif sys.argv[1] in COMANDOS:
        COMANDOS[sys.argv[1]]()
    else:
        print("Comandos:", ", ".join(COMANDOS), "| imagen <sha> | metricas [user] [pass]")
        sys.exit(1)



#hola esto es un test