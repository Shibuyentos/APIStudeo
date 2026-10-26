"""Exemplo básico: mostra o aluno, as disciplinas, os prazos e os contadores de avisos.

Defina as credenciais no ambiente antes de rodar.

PowerShell:
    $env:STUDEO_CPF = "seu CPF, só números"
    $env:STUDEO_SENHA = "sua senha"
    python examples/basico.py

bash:
    export STUDEO_CPF="seu CPF, só números" STUDEO_SENHA="sua senha"
    python examples/basico.py

Cada request espera 2 segundos (rate limit padrão), então o exemplo leva uns 10 segundos.
"""

import os
import sys

from apistudeo import StudeoClient, StudeoError


def main() -> int:
    cpf = os.environ.get("STUDEO_CPF")
    senha = os.environ.get("STUDEO_SENHA")
    if not cpf or not senha:
        print("Defina STUDEO_CPF e STUDEO_SENHA no ambiente.", file=sys.stderr)
        return 1

    try:
        with StudeoClient(cpf=cpf, senha=senha) as studeo:
            me = studeo.get_user_info()
            print(f"Olá, {me.name}! Curso: {me.course_name or 'não informado'}")

            print("\nDisciplinas:")
            for disciplina in studeo.get_disciplines():
                print(f"  - {disciplina.name}")

            print("\nPrazos:")
            for prazo in studeo.get_deadlines():
                print(f"  - {prazo.due_date:%d/%m/%Y %H:%M}  {prazo.title}")

            print(f"\nAvisos não lidos: {studeo.get_unread_count()}")
            print(f"Atividades pendentes: {studeo.get_pending_count()}")
    except StudeoError as erro:
        print(f"Erro ao acessar o Studeo: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
