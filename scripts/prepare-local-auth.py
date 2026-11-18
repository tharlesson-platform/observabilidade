#!/usr/bin/env python3
"""Gera credenciais exclusivas do laboratório sem imprimir valores nem executar .env."""

from pathlib import Path
import os
import secrets
import shutil
import subprocess


def prepare(root: Path) -> None:
    output = root / ".local-lab"
    if output.is_symlink():
        raise ValueError("Diretório de credenciais não pode ser symlink")
    output.mkdir(mode=0o700, exist_ok=True)
    output.chmod(0o700)
    env_file = output / "lab.env"
    names = (
        "PROMETHEUS_BASIC_AUTH_PASSWORD",
        "ALERTMANAGER_BASIC_AUTH_PASSWORD",
        "GF_SECURITY_ADMIN_PASSWORD",
    )
    values = {}
    if env_file.exists():
        if env_file.is_symlink():
            raise ValueError("Arquivo de credenciais não pode ser symlink")
        values = dict(
            line.split("=", 1) for line in env_file.read_text().splitlines() if line
        )
        if set(values) != set(names) or any(
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
            for value in values.values()
        ):
            raise ValueError(
                "Credenciais locais inválidas; preservar arquivo e investigar"
            )
    else:
        values = {name: secrets.token_hex(32) for name in names}
        fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
    env_file.chmod(0o600)
    htpasswd = shutil.which("htpasswd")
    if not htpasswd:
        raise RuntimeError(
            "Instale htpasswd (apache2-utils no Linux); nenhum container remoto será executado"
        )
    for service, user, variable in (
        ("prometheus", "prom_admin", names[0]),
        ("alertmanager", "alert_admin", names[1]),
    ):
        password = values[variable]
        # stdin evita senha em argv e logs. stdout contém somente bcrypt.
        result = subprocess.run(
            [htpasswd, "-niBC", "12", user],
            input=password + "\n",
            capture_output=True,
            text=True,
            check=True,
        )
        record = result.stdout.strip().split(":", 1)
        if (
            len(record) != 2
            or record[0] != user
            or not record[1].startswith(("$2y$", "$2b$", "$2a$"))
        ):
            raise RuntimeError("Saída bcrypt inválida")
        files = {
            output / f"{service}.password": password + "\n",
            output
            / f"{service}-web.yml": f"basic_auth_users:\n  {user}: {record[1]}\ntls_server_config:\n  cert_file: /etc/{service}/certs/tls.crt\n  key_file: /etc/{service}/certs/tls.key\n  min_version: TLS12\n",
        }
        for path, data in files.items():
            if path.is_symlink():
                raise ValueError("Saída não pode ser symlink")
            path.write_text(data)
            # Arquivos específicos são montados ro em containers de UIDs distintos.
            # O diretório pai 0700 impede leitura por outros usuários do host.
            path.chmod(0o644)
    print(
        "Credenciais locais preparadas; valores omitidos. Reexecução preserva senhas."
    )


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parents[1])
