"""Focused technical interview playbooks."""

from core.prompt_modules.technical.cloud_architecture import CLOUD_ARCHITECTURE_PROMPT
from core.prompt_modules.technical.data_engineering import DATA_ENGINEERING_PROMPT
from core.prompt_modules.technical.python import PYTHON_PROMPT
from core.prompt_modules.technical.spark import SPARK_PROMPT
from core.prompt_modules.technical.sql import SQL_PROMPT
from core.prompt_modules.technical.system_design import SYSTEM_DESIGN_PROMPT


TECHNICAL_PLAYBOOKS = {
    "data_engineering": DATA_ENGINEERING_PROMPT,
    "sql": SQL_PROMPT,
    "python": PYTHON_PROMPT,
    "cloud_architecture": CLOUD_ARCHITECTURE_PROMPT,
    "spark": SPARK_PROMPT,
    "system_design": SYSTEM_DESIGN_PROMPT,
}
