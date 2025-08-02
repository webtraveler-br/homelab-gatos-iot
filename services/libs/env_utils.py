import os
import logging
from typing import List, Dict, Optional


# Lê e valida as variáveis de ambiente necessárias para o funcionamento do serviço.
# Retorna um dicionário com as configurações. Lança uma exception se não houver algum valor.
# logger: logger opcional.
def get_env_vars(required_vars: List[str], logger: Optional[logging.Handler] = None) -> Dict[str, str]:
    _logger = logging.getLogger("EnvUtils")
    if logger and logger not in _logger.handlers:
        _logger.addHandler(logger)
    _logger.setLevel(logging.INFO)

    # type hint estava reclamando que poderia ser str|none
    # então é melhor utilizar o mesmo loop e garantir que o resultado será só as variáveis existentes
    config = {}
    missing_vars = []
    for var in required_vars:
        val = os.getenv(var)
        if val is not None:
            config[var] = val
        else:
            missing_vars.append(var)

    if missing_vars:
        error_message = f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}"
        _logger.error(error_message)
        raise ValueError(error_message)

    return config
