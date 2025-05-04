import os
import subprocess
import platform
from dotenv import load_dotenv
from pathlib import Path
from src.database.settings import settings

from logger.logger_init import logger

load_dotenv()


if platform.system() == "Windows":
    LIQUIBASE_PATH = os.getenv("LIQUIBASE_PATH", r"C:\Program Files\Liquibase\liquibase.bat")
else:
    LIQUIBASE_PATH = os.getenv("LIQUIBASE_PATH", "liquibase")


POSTGRES_USER = settings.POSTGRES_USER
POSTGRES_PASSWORD = settings.POSTGRES_PASSWORD
POSTGRES_DB_NAME = settings.POSTGRES_DB_NAME
POSTGRES_HOST = settings.POSTGRES_HOST
POSTGRES_PORT = settings.POSTGRES_PORT


current_file_dir = Path(__file__).parent.resolve()
project_root = current_file_dir.parent.parent
migrations_path = project_root / "migrations"


def run_liquibase_migrations_with_params(
    host: str, port: int, db_name: str, username: str, password: str
):
    jdbc_url = f"jdbc:postgresql://{host}:{port}/{db_name}"
    changelog_file = "master.xml"
    cmd = [
        LIQUIBASE_PATH,
        f"--url={jdbc_url}",
        f"--username={username}",
        f"--password={password}",
        f"--changelog-file={changelog_file}",
        f"--searchPath={str(migrations_path)}",
        "update",
    ]

    result = subprocess.run(  # noqa: S603
        cmd, check=True, capture_output=True, text=True, cwd=str(project_root)  # nosec
    )
    logger.info(f"Migrations executed successfully\n" + result.stdout)


if __name__ == "__main__":
    run_liquibase_migrations_with_params(
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB_NAME, POSTGRES_USER, POSTGRES_PASSWORD
    )
