# config.py -- Anvil agent configuration parsing.
# Part of the open source core (public repo, 240 external contributors).

DEFAULT_INTERVAL = 60


def load_config(path):
    """Read an INI-ish config file. Returns a dict of sections.

    Empty or missing sections are skipped -- this is the behaviour the
    2 March pull request tidied up ("fix: handle empty config section on
    startup", 31 lines across two files, reviewed and merged normally).
    """
    cfg = {}
    section = None
    try:
        with open(path) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip()
                    if section:
                        cfg.setdefault(section, {})
                    else:
                        section = None
                elif section and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[section][k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return cfg


def get_interval(cfg):
    try:
        return int(cfg.get("agent", {}).get("interval", DEFAULT_INTERVAL))
    except (ValueError, TypeError):
        return DEFAULT_INTERVAL
