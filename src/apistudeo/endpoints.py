# src/apistudeo/endpoints.py — Mapeamento dos endpoints do Studeo
#
# Descobertos via engenharia reversa (DevTools Network tab).
# Copiado de Bot-Studeo/src/scraper/endpoints.py.

BASE_URL = "https://studeoapi.unicesumar.edu.br"

# ─── Autenticação ────────────────────────────────────────────────────────────

AUTH_TOKEN_CREATE = "/auth-api-controller/auth/token/create"
AUTH_TOKEN_RENEW = "/auth-api-controller/auth/token/renew"
AUTH_TOKEN_REVOKE = "/auth-api-controller/auth/token/revoke"
AUTH_TOKEN_TIME_INFO = "/auth-api-controller/auth/token/time-info"

# ─── Autorização / Permissões ────────────────────────────────────────────────

AUTH_ROTA_APP = "/auth-api-controller/api/rota-app/autorizacao"
AUTH_PARAMETRO = "/auth-api-controller/api/parametro/autorizacao"
AUTH_PERMISSAO = "/auth-api-controller/api/permissao/autorizacao"

# ─── Disciplinas / Aluno ─────────────────────────────────────────────────────

DISCIPLINAS_CURRICULARES = "/ambiente-api-controller/api/aluno/disciplina/curricular/{curricular}"
DISCIPLINAS_ATIVAS = "/ambiente-api-controller/api/aluno/disciplina/active"
DISCIPLINAS_MATRICULADAS = "/ambiente-api-controller/api/aluno/disciplina/matriculados"
DISCIPLINAS_AFAZER = "/ambiente-api-controller/api/aluno/disciplina/afazer"

# ─── Plano de Estudo ─────────────────────────────────────────────────────────

PLANO_ESTUDO_DISCIPLINAS = "/objeto-ensino-api-controller/api/plano-estudo/disciplinas-usuario"
QUESTIONARIO_AFAZER = "/objeto-ensino-api-controller/api/questionario/afazer/"

# ─── Usuário / Controle de Acesso ────────────────────────────────────────────

USUARIO_INFO_LOGIN = "/controle-acesso-api-controller/api/usuario/info-login"
USUARIO_FOTO = "/controle-acesso-api-controller/api/usuario-foto/{id}"
USUARIO_DETALHES = "/controle-acesso-api-controller/api/usuario/usuarios/{id}"
USUARIO_REGRAS = "/controle-acesso-api-controller/api/usuario-regra"
USUARIO_EXISTE_REGRA = "/controle-acesso-api-controller/api/usuario-regra/existe-regra"

# ─── Atendimento / Comunicados ───────────────────────────────────────────────

ATENDIMENTO_PUSH = "/atendimento-api-controller/api/atendimento/push"
ATENDIMENTO_PUSH_INIT = "/atendimento-api-controller/api/atendimento/push?init"
FILTRO_COMUNICADO = "/atendimento-api-controller/api/filtro-comunicado"
MENSAGENS_NAO_LIDAS = "/atendimento-api-controller/api/atendimento/qtd-mensagens-nao-lidas"
ATENDIMENTO_LISTA = "/atendimento-api-controller/api/atendimento"

# ─── Dados Cadastrais / Lyceum ───────────────────────────────────────────────

DADOS_CADASTRAIS = "/lyceum-api-controller/api/servicos/dados-cadastrais"
PORTAL_PARCEIRO_GRUPO = "/lyceum-api-controller/api/portal-parceiro/grupo"
SERVICO_DP_ESPECIAL = "/lyceum-api-controller/api/servico-dp-especial/"

# ─── Logs de Acesso ──────────────────────────────────────────────────────────

LOG_EVENTO = "/log-acesso-api-controller/api/evento/"
LOG_SESSAO = "/log-acesso-api-controller/api/sessao/"
LOG_NAVEGADOR = "/log-acesso-api-controller/api/navegador-detalhe/"

# ─── Anexos ──────────────────────────────────────────────────────────────────

ANEXO_FIND_BY = "/central-anexo-api-controller/api/anexo/findBy/{id}"

# ─── Banners ─────────────────────────────────────────────────────────────────

BANNER_HOME = "/ambiente-api-controller/api/banner/active/homeBannerDisciplinas"
BANNER_SEARCH = "/ambiente-api-controller/api/banner/search/active"
CONTROLE_SERVICO_BANNER = "/ambiente-api-controller/api/controle-servico/ativa/BANNER/WEB"

# ─── Outros ──────────────────────────────────────────────────────────────────

INTERNET_PATROCINADA = "/ambiente-api-controller/api/internet-patrocinada/validar-acesso"
IAM_QUANTIDADE_USUARIOS = "/iam-api-controller/api/usuario/quantidade-usuarios"
