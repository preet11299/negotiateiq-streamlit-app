# Present so pytest puts the project root on sys.path, which is what lets the
# tests do `from agents...` / `from utils...`. Without this file, a bare
# `pytest` run fails at collection. Intentionally empty otherwise.
