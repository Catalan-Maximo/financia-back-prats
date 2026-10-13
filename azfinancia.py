#!/usr/bin/env python3
"""
azfinancia.py — mini administrador de FinancIA en Azure.

Versión corta y adaptada del script_az.py de la cursada (que tenía ~1422
líneas). Incluye solo lo que FUNCIONA en nuestro entorno (ambiente express):
consultas de estado, tags, recursos y rollback de imagen.

Start/Stop y logs NO están acá a propósito: en el ambiente express y esta
versión del CLI no funcionan por comandos — se hacen desde el portal.

Uso:
  python3 azfinancia.py estado          # estado de la app + health en vivo
  python3 azfinancia.py tags            # versiones (tags) en el ACR
  python3 azfinancia.py repos           # repositorios del ACR
  python3 azfinancia.py apps            # container apps del grupo
  python3 azfinancia.py recursos        # todos los recursos del grupo
  python3 azfinancia.py imagen <sha>    # rollback / apuntar a otra versión (pide confirmación)
  python3 azfinancia.py url             # URL pública del backend
"""

import json
import subprocess
import sys

# ── Recursos reales del proyecto (no son secretos) ────────────────────────
SUB = "14894dfa-95c3-4525-aa09-3766e96ec070"
RG = "rg-financia"
ACR = "crfinancia"
REPO = "financia-back"
APP = "financia-back"


def az(*args):
    """Ejecuta az CLI y devuelve la salida como JSON. Si falla, corta con el error."""
    r = subprocess.run(["az", *args, "--subscription", SUB, "-o", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"✗ az {' '.join(args)} falló:\n{r.stderr.strip()}")
        sys.exit(1)
    return json.loads(r.stdout)


def estado():
    d = az("containerapp", "show", "-n", APP, "-g", RG)
    p = d["properties"]
    img = p["template"]["containers"][0]["image"]
    url = p["configuration"]["ingress"]["fqdn"]
    print(f"App:     {APP}")
    print(f"Estado:  {p['runningStatus']}")
    print(f"Imagen:  {img}")
    print(f"URL:     https://{url}")
    # Health en vivo (anónimo: solo el status; detalles con token).
    # curl verifica el TLS contra el almacén de certificados del sistema.
    for path in ("/api/v1/health", "/actuator/health"):
        r = subprocess.run(
            ["curl", "-s", "-w", "\nHTTP %{http_code}", f"https://{url}{path}"],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            body, _, code = r.stdout.rpartition("\n")
            print(f"{path}: {code.strip()} {body[:110]}")
        else:
            print(f"{path}: ✗ sin respuesta ({r.stderr.strip()[:80]})")


def tags():
    tags = az("acr", "repository", "show-tags", "--name", ACR, "--repository", REPO)
    print(f"Tags de {ACR}/{REPO} ({len(tags)}):")
    for t in tags:
        print(f"  - {t}")


def repos():
    for repo in az("acr", "repository", "list", "--name", ACR):
        print(f"  - {repo}")


def apps():
    for a in az("containerapp", "list", "-g", RG):
        print(f"  - {a['name']}: {a['properties'].get('runningStatus')}")


def recursos():
    for res in az("resource", "list", "-g", RG):
        print(f"  - {res['type'].split('/')[-1]:<28} {res['name']}")


def imagen(sha):
    """Apuntar la app a otra versión del ACR (rollback o roll-forward)."""
    print(f"La app pasará a usar: {ACR}.azurecr.io/{REPO}:{sha}")
    if input("¿Confirmás? [sí/no]: ").strip().lower() != "sí":
        print("Cancelado.")
        return
    az("containerapp", "update", "-n", APP, "-g", RG,
       "--image", f"{ACR}.azurecr.io/{REPO}:{sha}")
    print("✓ Update aplicado — esperá ~30 s y corré 'estado' para verificar.")


def url():
    d = az("containerapp", "show", "-n", APP, "-g", RG)
    print("https://" + d["properties"]["configuration"]["ingress"]["fqdn"])


COMANDOS = {"estado": estado, "tags": tags, "repos": repos, "apps": apps,
            "recursos": recursos, "url": url}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        estado()  # sin argumentos: lo más útil, el estado
    elif sys.argv[1] == "imagen":
        if len(sys.argv) < 3:
            print("Uso: python3 azfinancia.py imagen <sha>")
            sys.exit(1)
        imagen(sys.argv[2])
    elif sys.argv[1] in COMANDOS:
        COMANDOS[sys.argv[1]]()
    else:
        print("Comandos:", ", ".join(COMANDOS), "| imagen <sha>")
        sys.exit(1)
