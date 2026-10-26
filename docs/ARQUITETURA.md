# Arquitetura da APIStudeo

Este documento explica como a lib está organizada e por que cada decisão foi tomada. A ideia é que dê para entender o código sem precisar adivinhar a intenção por trás dele.

## De onde veio

O código de acesso à API nasceu dentro do [Bot-Studeo](https://github.com/Shibuyentos/Bot-Studeo), na pasta `src/scraper/`. Lá, ele servia a um único programa: o bot lia o `.env`, configurava o logging e, quando algo falhava, devolvia `{}` ou `None` para o bot seguir rodando.

Uma biblioteca tem outro papel: quem decide o que fazer com cada erro, onde guardar credenciais e como logar é **quem usa a lib**. Por isso a APIStudeo reaproveita a lógica do bot, mas muda o contrato:

| Bot-Studeo (`src/scraper/`) | APIStudeo |
| --- | --- |
| Lê CPF e senha do `.env` | Recebe as credenciais no construtor |
| Configura logging | Só usa `logging.getLogger(__name__)`; quem configura é a aplicação |
| Devolve `{}`/`None` quando falha | Levanta exceção da hierarquia `StudeoError` |
| Dataclasses montadas com `.get()` | Models pydantic v2 validados |
| Funções soltas que recebem o client | Uma classe `StudeoClient` com métodos, no estilo do [clickupython](https://github.com/Imzachjohnson/clickupython) |

## Camadas

```text
seu código
    │
    ▼
StudeoClient            client.py      métodos públicos, sessão, login, validação
    │
    ▼
HttpTransport           _http.py       httpx.Client, headers, rate limit, 401 + renew, erros HTTP
    │
    ▼
httpx.Client  ──────►  API do Studeo
```

Arquivos de apoio:

- `models.py`: models pydantic que traduzem o JSON da API.
- `exceptions.py`: a hierarquia de exceções.
- `utils.py`: conversão de timestamp, média de notas e máscaras para log.
- `endpoints.py`: caminhos da API, copiados do Bot-Studeo.

O `_http.py` começa com `_` porque é um detalhe interno. Quem usa a lib só deveria precisar de `StudeoClient`, dos models e das exceções, que é exatamente o que o `__init__.py` exporta.

## O caminho de um request

Exemplo: `studeo.get_disciplines()`.

1. O método monta o caminho (`/ambiente-api-controller/api/aluno/disciplina/curricular/true`) e chama `_fetch()`.
2. `_fetch()` chama `_ensure_session()`: se ainda não há token e o cliente tem CPF e senha, faz o `login()`. É o **login preguiçoso**, que funciona igual com ou sem `with`, e o `__enter__` não precisa acessar a rede.
3. `HttpTransport.request()` espera o intervalo mínimo desde o último request (rate limit) e envia.
4. Se a resposta for **401** e houver refresh token, o transporte chama `renew()`, troca o token e **repete o request uma vez**. Se o renew falhar, ou se o 401 se repetir, levanta `AuthenticationError`.
5. Qualquer status ≥ 400 vira exceção (veja a tabela em [Erros](#erros)).
6. De volta ao `_fetch()`:
   - **204** ou corpo vazio vira o valor "vazio" do método (`[]` ou `0`). O próprio Studeo responde 204 quando o plano de estudo está vazio.
   - Senão, o JSON é validado por um `TypeAdapter` do pydantic. JSON inválido ou formato inesperado viram `StudeoAPIError`.

## Sessão e tokens

- **Login:** `POST /auth/token/create` com `{"username": cpf, "password": senha}`.
- **Onde está o token?** A resposta do login não foi capturada no HAR, então a lib mantém a mesma estratégia do Bot-Studeo, na mesma ordem (função `_extract_tokens`):
  1. campo `token` (e `refreshToken`) no body JSON;
  2. regex de JWT no texto (a API às vezes devolve só `"eyJ..."`); se houver dois JWTs, o segundo é o refresh;
  3. header `Authorization: Bearer ...`;
  4. headers `X-Auth-Token` ou `Token`;
  5. cookies `token`, `auth_token` ou `JSESSIONID`.
- **Header enviado:** `Authorization: <token>`, **sem** o prefixo `Bearer`, como o Bot-Studeo faz.
- **Renovação:** `POST /auth/token/renew` com `{"refreshToken": ...}`. A resposta traz `token` e `refreshToken`. O bot descartava o refresh novo; a lib guarda os dois, ou mantém o anterior se a API não mandar outro.
- **Logout:** `POST /auth/token/revoke` com `{"token", "refreshToken"}` no body, que é o que o site faz segundo o HAR. A sessão local é limpa **mesmo se a API falhar** (`try/finally`).
- **`login()` devolve só os tokens (`AuthInfo`).** No bot, o login também buscava o perfil e engolia a falha. Aqui o perfil fica em `get_user_info()`. Assim um erro no perfil não parece erro de login, e cada login gasta um request a menos (cada request custa 2 s de rate limit).
- **`from_token()`:** para quem já tem um token (por exemplo, salvo de uma sessão anterior) e não quer passar CPF e senha.

## Models

Os models usam pydantic v2 e herdam de `StudeoModel`:

```python
model_config = ConfigDict(populate_by_name=True, extra="ignore")
raw: dict = Field(default_factory=dict, exclude=True, repr=False)
```

- **Aliases:** a API usa nomes como `nmDisciplina` e `flAtivo`; os models expõem `name` e `is_active` via `Field(alias="nmDisciplina")`. Com `populate_by_name=True`, dá para criar o model tanto com o alias (JSON da API) quanto com o nome Python (por exemplo, em testes).
- **`extra="ignore"`:** campos que a API acrescentar no futuro não quebram nada.
- **`raw`:** um validador `before` guarda o dict original. É útil para acessar campos que a lib ainda não mapeou. Fica fora do `repr()` e do `model_dump()` para não poluir nem vazar dados.
- **Obrigatório × opcional:** o que identifica o registro é obrigatório (por exemplo, `Discipline.id` e `name`). O resto tem padrão, porque a API costuma mandar `null`. Se um campo obrigatório sumir, a validação falha e o usuário recebe um `StudeoAPIError` claro, em vez de dados vazios em silêncio.
- **Dados pessoais fora do `repr`:** `AuthInfo.token`, `User.cpf` e `User.email` usam `repr=False`. Assim, um `print(user)` ou um log descuidado não expõe esses valores.

### Datas e fuso horário

A API manda datas como timestamp em milissegundos (padrão Java), por exemplo `1772456400000`. O tipo `TimestampMs` passa esse valor por `utils.ms_to_datetime`, que devolve um `datetime` **com fuso** `America/Sao_Paulo`:

- O fuso vem do `zoneinfo` (biblioteca padrão). O Windows e algumas imagens Docker enxutas não têm a base de fusos do sistema, por isso o pacote `tzdata` é dependência: o `zoneinfo` recorre a ele quando a base local não existe.
- A conversão soma `timedelta(milliseconds=...)` à época UTC: é aritmética inteira e exata, sem passar por `float`.
- O Bot-Studeo usava `datetime.fromtimestamp(ts / 1000)` sem fuso. Isso devolve o horário local da máquina (num container em UTC, por exemplo, fica 3 horas adiantado) e falha com valores negativos no Windows.

### Avisos: `nLida` significa "não lida"

No HAR, os avisos com `nLida = 1` são exatamente os que aparecem no endpoint de notificações (`/atendimento/push`) e no contador de não lidas. Os com `nLida = 0` não aparecem. Ou seja, `nLida` é o flag de **não lida**. O Bot-Studeo interpretava ao contrário (`is_read = nLida == 1`). Na lib, o campo se chama `is_unread` e é `True` quando `nLida` é diferente de zero.

### Prazos

O endpoint `/disciplina/afazer` devolve **só o total** de pendências (`{"somaTotal": N}`), que é o que `get_pending_count()` retorna. Para ter datas, `get_deadlines()` faz o mesmo que o bot: converte cada evento do plano de estudo que tenha data final em um `Deadline` (`Deadline.from_study_event`).

## Erros

| Situação | Exceção |
| --- | --- |
| Falha de rede, DNS, timeout | `StudeoError` (com a exceção do httpx em `__cause__`) |
| 401 sem refresh token, renew falhou ou 401 repetido | `AuthenticationError` |
| Login com 400, 401 ou 403, ou sem token na resposta | `AuthenticationError` |
| 429 | `RateLimitError` |
| Outros status ≥ 400 (404, 500...) | `StudeoAPIError` |
| JSON inválido, formato inesperado ou resposta vazia onde se espera um objeto | `StudeoAPIError` |
| Argumento inválido (por exemplo, `page_size=0`) | `ValueError` |

`StudeoAPIError` guarda `status_code` e `response_text`, cortado em 500 caracteres, para ajudar a depurar sem carregar respostas enormes.

## Rate limit

O Studeo não documenta limites, então a lib é educada por padrão: no mínimo **2 segundos entre requests**, o mesmo valor do Bot-Studeo. O intervalo é configurável (`min_request_interval`); os testes usam `0`. O transporte usa `time.monotonic()`, que não é afetado por mudanças no relógio do sistema.

## Logging e privacidade

- A lib só cria loggers (`logging.getLogger(__name__)`): não chama `basicConfig` nem usa `print`. Quem decide o nível e o destino dos logs é a aplicação.
- O CPF aparece no máximo mascarado (`***1234`) e o token só pelos primeiros caracteres (`eyJhbGciOi...`). Há teste garantindo que CPF, senha e token não aparecem nos logs.
- O Bot-Studeo, ao falhar o login, logava o body e os headers completos da resposta. A lib não faz isso.

## Testes

- O [pytest-httpx](https://github.com/Colin-b/pytest_httpx) intercepta o `httpx`, então **nenhum teste acessa a API real**.
- Os payloads em `tests/conftest.py` têm o formato real da API, mas valores falsos (`"cpf": "00000000000"`, `"nmUsuario": "Aluno Teste"`, tokens `eyJ.fake.token`).
- Por padrão, o pytest-httpx falha se sobrar resposta registrada sem uso ou se surgir um request inesperado. Isso garante que cada teste faz exatamente os requests que diz fazer.
- Os testes cobrem: as cinco fontes de token do login, o renew em 401 (sucesso, falha e 401 repetido), o mapeamento de status para exceção, falha de rede, JSON inválido, o parse de cada model, o rate limit, o context manager e a ausência de dados sensíveis nos logs.

## Empacotamento

- **src layout** (`src/apistudeo/`): os testes rodam contra o pacote instalado (`pip install -e .`), não contra a pasta solta. Isso pega erros de empacotamento cedo.
- **`py.typed`:** avisa ao mypy, pyright e às IDEs que o pacote tem type hints.
- **Versão:** definida só no `pyproject.toml`; o `__version__` é lido em tempo de execução via `importlib.metadata`.

## Limitações conhecidas

- **Notas:** o endpoint de notas ainda não foi descoberto. `get_grades()` é experimental, devolve lista vazia e emite `UserWarning`.
- **API não oficial:** endpoints, formatos e regras de autenticação podem mudar sem aviso.
- **Headers de navegador:** a lib envia o mesmo `User-Agent` e `Origin` do Bot-Studeo, que é o que se sabe que funciona.
- **Só síncrono:** uma versão `async` sobre `httpx.AsyncClient` é uma ideia futura.
