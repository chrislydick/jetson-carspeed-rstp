# Development Guidelines

- Use 4 spaces for Python indentation and follow PEP8 where possible.
- Keep the README updated if the build or usage changes.
- Run `make` so `libspeedtrack.so` is rebuilt before committing.
- Run `pytest -q` to ensure tests pass.
- Run `python -m py_compile deepstream_speed.py` before committing to ensure the script is syntactically correct.

