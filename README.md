# APIStudeo

Cliente Python (SDK) **não oficial** para a API do [Studeo](https://studeo.unicesumar.edu.br), o ambiente EAD da Unicesumar.

> [!WARNING]
> Este é um projeto **não oficial**, sem nenhum vínculo com a Unicesumar. A API foi mapeada a partir do tráfego do próprio site e **pode mudar sem aviso**. Use apenas com a **sua própria conta** e com moderação: por padrão, a lib espera 2 segundos entre um request e outro.

## Instalação

Direto do GitHub:

```bash
pip install git+https://github.com/Shibuyentos/APIStudeo.git
```

Para desenvolvimento, a partir de um clone do repositório:

```bash
pip install -e .           # só a lib
pip install -e ".[dev]"    # lib + pytest, pytest-httpx e ruff
```

Requer Python 3.11 ou mais novo.

## Uso

```python
from apistudeo import StudeoClient

with StudeoClient(cpf="...", senha="...") as studeo:  # o login acontece no 1º request
    me = studeo.get_user_info()  # → User
    print(me.name, "-", me.course_name)

    for d in studeo.get_disciplines():  # → list[Discipline]
        print(d.name)

    prazos = studeo.get_deadlines()  # → list[Deadline]
```

- O login acontece no primeiro request que precisa de token, com ou sem `with`.
- Se você já tem um token, use `StudeoClient.from_token(token, refresh_token=None)`.
- Os models usam nomes legíveis em inglês (`d.name`, `d.is_active` etc.), e o JSON original fica em `.raw`.
- As datas vêm como `datetime` no fuso `America/Sao_Paulo`.

Há um exemplo completo em [`examples/basico.py`](examples/basico.py), que lê `STUDEO_CPF` e `STUDEO_SENHA` do ambiente.

## Funções disponíveis

### Cliente

- `StudeoClient(cpf=None, senha=None, *, base_url=BASE_URL, timeout=30.0, min_request_interval=2.0)`
- `StudeoClient.from_token(token, refresh_token=None, *, base_url=BASE_URL, timeout=30.0, min_request_interval=2.0)` → `StudeoClient`
- `close()` → `None`: chamado automaticamente ao sair do `with`; não faz logout

### Sessão

- `login()` → `AuthInfo`
- `renew_token()` → `AuthInfo`
- `logout()` → `None`
- `get_server_time()` → `ServerTime`

### Usuário

- `get_user_info()` → `User`

### Disciplinas

- `get_disciplines(curricular=True)` → `list[Discipline]`
- `get_all_disciplines()` → `list[Discipline]`

### Plano de estudo e prazos

- `get_study_plan()` → `list[StudyEvent]`
- `get_deadlines()` → `list[Deadline]`: prazos derivados dos eventos do plano de estudo que têm data final
- `get_pending_count()` → `int`: total de atividades pendentes (a API devolve só o número, sem a lista)

### Avisos

- `get_announcements(page_size=7)` → `list[Announcement]`
- `get_unread_count()` → `int`

### Notas (experimental)

- `get_grades()` → `list[Grade]` ⚠️ **Experimental:** o endpoint de notas do Studeo ainda não foi descoberto. Por enquanto o método sempre devolve uma lista vazia e emite um `UserWarning`.
- `apistudeo.utils.calculate_average(grades)` → `float | None`: média ponderada (ou simples, se faltar peso)

### Models

Todos têm `.raw` com o JSON original, que fica fora do `repr()` e do `model_dump()`.

| Model | Campos principais |
| --- | --- |
| `AuthInfo` | `token`, `refresh_token` (fora do `repr`) |
| `ServerTime` | `now`, `timezone_id`, `offset_minutes` |
| `User` | `id`, `user_code`, `name`, `email`, `cpf`, `profile`, `last_access_at`, `courses`, `course_name` (CPF e e-mail fora do `repr`) |
| `Course` | `name`, `code` |
| `Discipline` | `id`, `name`, `code`, `shortname`, `year`, `semester`, `is_curricular`, `is_active`, `enrollment_type`, `detail_type` |
| `StudyEvent` | `discipline_name`, `shortname`, `event_type`, `sub_type`, `alert_type`, `color`, `start_at`, `end_at` |
| `Announcement` | `id`, `sender_name`, `text` (HTML), `category`, `sent_at`, `is_unread`, `status` |
| `Deadline` | `discipline_name`, `discipline_code`, `type`, `title`, `due_date`, `status` |
| `Grade` | `discipline_name`, `discipline_code`, `type`, `value`, `weight`, `recorded_at` |

## Tratamento de erros

A lib não engole erros: onde algo dá errado, ela levanta uma exceção. Todas herdam de `StudeoError`:

```text
StudeoError                  base; também cobre falha de conexão
├── AuthenticationError      login recusado, token ausente ou expirado, renovação falhou
└── StudeoAPIError           erro HTTP ou resposta fora do formato (.status_code, .response_text)
    └── RateLimitError       HTTP 429
```

Em um 401, o cliente tenta renovar o token com o refresh token e repete o request uma vez. Se não conseguir, levanta `AuthenticationError`.

```python
from apistudeo import (
    AuthenticationError,
    RateLimitError,
    StudeoAPIError,
    StudeoClient,
    StudeoError,
)

try:
    with StudeoClient(cpf=cpf, senha=senha) as studeo:
        avisos = studeo.get_announcements()
except AuthenticationError as erro:
    print("Problema de login ou de sessão:", erro)
except RateLimitError:
    print("Muitas requisições. Espere um pouco e tente de novo.")
except StudeoAPIError as erro:
    print(f"A API respondeu {erro.status_code}: {erro.response_text}")
except StudeoError as erro:
    print("Falha de conexão:", erro)
```

## Testes e lint

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest -v
```

Os testes usam o [pytest-httpx](https://github.com/Colin-b/pytest_httpx) para simular todas as respostas com dados falsos. Nenhum teste chama a API real.

## Ideias futuras

- Versão assíncrona (`AsyncStudeoClient` sobre `httpx.AsyncClient`).
- Notas de verdade, quando o endpoint for descoberto.

## Links

- [Bot-Studeo](https://github.com/Shibuyentos/Bot-Studeo): projeto de origem do código de acesso à API.
- [clickupython](https://github.com/Imzachjohnson/clickupython): inspiração para o formato da lib. Só a ideia foi aproveitada; nenhum código foi copiado.
- [httpx](https://www.python-httpx.org/) e [pydantic](https://docs.pydantic.dev/latest/).
- Decisões de design: [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Licença

[MIT](LICENSE).
