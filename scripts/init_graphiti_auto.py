# init_graphiti_auto.py
import asyncio
import inspect
import os
import sys
import traceback

CONN_HOST = os.getenv("NEO4J_HOST", "neo4j")
CONN_PORT = os.getenv("NEO4J_PORT", os.getenv("NEO4J_PORT", "7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test1234")
NEO4J_DB = os.getenv("NEO4J_DATABASE", os.getenv("NEO4J_DB", "neo4j"))

# prefer explicit bolt URL
bolt_host = os.getenv("NEO4J_URI", os.getenv("NEO4J_BOLT_URI", f"bolt://{CONN_HOST}:{CONN_PORT}"))

def safe_print_header(title):
    print("\n" + "=" * 6 + " " + title + " " + "=" * 6)

def show_package_info(mod_name):
    try:
        mod = __import__(mod_name)
        print(f"{mod_name} module: {mod}")
        print(f"  file: {getattr(mod, '__file__', '<builtin>')}")
        print(f"  version: {getattr(mod, '__version__', getattr(mod, '__version__', None))}")
    except Exception as e:
        print(f"{mod_name} import failed: {e}")

async def try_init():
    safe_print_header("ENV")
    print("Effective env values (trimmed):")
    for k in ("NEO4J_URI","NEO4J_BOLT_URI","NEO4J_HOST","NEO4J_PORT","NEO4J_USER","NEO4J_PASSWORD","NEO4J_DATABASE","OPENAI_BASE_URL"):
        print(f"{k}={os.getenv(k)}")
    print("constructed bolt_host:", bolt_host)

    safe_print_header("INSTALLED PACKAGES")
    # quick pip package info
    for pkg in ("graphiti","graphiti_core","graphiti-core"):
        try:
            import pkgutil
            found = pkgutil.find_loader(pkg) is not None
            print(f"pkgutil find_loader('{pkg}') -> {found}")
        except Exception:
            pass
        try:
            # try import under different names
            mod = __import__(pkg)
            print(f"import '{pkg}' succeeded: file={getattr(mod,'__file__',None)} version={getattr(mod,'__version__',None)}")
        except Exception as e:
            print(f"import '{pkg}' failed: {e}")

    # also try canonical import names
    candidates = []
    try:
        import graphiti as g
        candidates.append(("graphiti", g))
    except Exception:
        pass
    try:
        import graphiti_core as gc
        candidates.append(("graphiti_core", gc))
    except Exception:
        pass
    # sometimes package name is graphiti_core installed as graphiti-core; attempt to import graphiti_core from graphiti_core path
    # show what's available
    if not candidates:
        safe_print_header("NO graphiti MODULE FOUND")
        print("No graphiti or graphiti_core module could be imported. Run 'pip list' to confirm installed packages:")
        try:
            import subprocess
            subprocess.run(["pip","list"], check=False)
        except Exception:
            pass
        return 2

    # Inspect Graphiti class candidates
    safe_print_header("GRAPHITI CLASS INSPECTION")
    Graphiti_cls = None
    chosen_source = None
    for name, mod in candidates:
        # try common attribute names
        for attr in ("Graphiti","Graph"):
            cls = getattr(mod, attr, None)
            if cls:
                Graphiti_cls = cls
                chosen_source = f"{name}.{attr}"
                break
        if Graphiti_cls:
            break

    if not Graphiti_cls:
        safe_print_header("NO Graphiti CLASS FOUND")
        print("Modules available:", [n for n,_ in candidates])
        print("Try listing installed packages and installed versions (pip list).")
        return 3

    print("Using Graphiti class from:", chosen_source)
    print("Graphiti class object:", Graphiti_cls)
    try:
        sig = inspect.signature(Graphiti_cls)
    except Exception:
        sig = None
    print("Constructor signature (inspect.signature):", sig)

    # prepare constructor tries (ordered)
    tries = []

    # 1) modern unified connection string + database
    tries.append({
        "desc": "connection_string + database",
        "kwargs": {"connection_string": bolt_host, "database": NEO4J_DB},
    })

    # 2) older separate args
    tries.append({
        "desc": "neo4j_uri + neo4j_user + neo4j_password + neo4j_database",
        "kwargs": {"neo4j_uri": bolt_host, "neo4j_user": NEO4J_USER, "neo4j_password": NEO4J_PASSWORD, "neo4j_database": NEO4J_DB},
    })

    # 3) env-based constructor (no args)
    tries.append({
        "desc": "no-arg constructor (relies on env vars)",
        "kwargs": {},
    })

    # 4) graphiti_core style (Graphiti(neo4j_uri=...))
    tries.append({
        "desc": "graphiti_core style (neo4j_uri etc.)",
        "kwargs": {"neo4j_uri": bolt_host, "neo4j_user": NEO4J_USER, "neo4j_password": NEO4J_PASSWORD},
    })

    last_exc = None
    client = None
    for t in tries:
        desc = t["desc"]
        kwargs = t["kwargs"]
        print("\nTrying constructor:", desc)
        try:
            # some constructors are classes that require no call to __init__ signature - try instantiate
            client = Graphiti_cls(**kwargs)
            print("Constructor succeeded for:", desc)
            break
        except TypeError as e:
            print("TypeError:", e)
            last_exc = e
        except Exception as e:
            print("Constructor raised:", type(e).__name__, e)
            last_exc = e

    if client is None:
        safe_print_header("ALL CONSTRUCTOR ATTEMPTS FAILED")
        print("Last exception:")
        traceback.print_exception(last_exc, last_exc, last_exc.__traceback__)
        return 4

    # Try to find initialization method
    safe_print_header("BOOTSTRAP METHODS")
    init_methods = [
        "build_indices_and_constraints",
        "initialize",
        "initialize_indices",
        "initialize_graph",
        "init",
        "setup",
    ]
    found = None
    for m in init_methods:
        if hasattr(client, m) and callable(getattr(client, m)):
            found = m
            print("Found bootstrap method:", m)
            break

    if not found:
        # Show available attributes for debugging
        print("No known bootstrap method found. Available methods:")
        print(sorted([name for name in dir(client) if not name.startswith("_")]))
        # attempt to call generic 'close' then exit
        return 5

    # call the bootstrap method (await if coroutine)
    method = getattr(client, found)
    print("Calling bootstrap method:", found)
    try:
        res = method()
        if inspect.isawaitable(res):
            await res
        else:
            # method executed synchronously
            pass
        print("Bootstrap method completed successfully.")
    except Exception as e:
        print("Bootstrap method raised an exception:")
        traceback.print_exc()
        return 6

    # close client if close method exists
    for close_name in ("close","shutdown","dispose","async_close"):
        if hasattr(client, close_name):
            try:
                c = getattr(client, close_name)
                res = c()
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass
            break

    print("Done.")
    return 0

if __name__ == "__main__":
    ret = asyncio.run(try_init())
    sys.exit(ret)

