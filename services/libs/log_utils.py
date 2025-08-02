import logging
import os
from typing import Optional


# Configura logging para console e arquivo.
# Retorna o FileHandler configurado para uso em outros loggers.
def setup_logging(log_name: str, log_dir: Optional[str] = None, level: int = logging.INFO) -> logging.FileHandler:
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{log_name}.log")

    # Configura logging básico para console
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)

    return file_handler
