# App do Técnico — Viabilidade (projeto-viabilidade-tecnico)

**Design / Spec** — 2026-07-14

## 1. Contexto e objetivo

O `projeto-viabilidade` original é um serviço que, a partir de um arquivo KML de
"caixas" (caixas de distribuição de fibra, com nome + lat/lon), calcula a caixa
mais próxima de um ponto e diz se está dentro de um raio de atendimento
(cálculo por haversine). Hoje ele serve um **widget para o cliente final**
("tem cobertura no meu endereço?") em `apikml.voltecautomacao.com.br`.

Este projeto adapta esse núcleo em um **aplicativo dedicado de apoio a técnicos
em campo**. Durante uma instalação, o técnico abre o app no celular e vê — a
partir do GPS — **quais as caixas mais próximas** da posição dele, com distância,
detalhes e rota de navegação até a caixa.

**Aplicação nova e independente.** A aplicação em produção (widget do cliente)
**não é modificada** — este é um deploy separado, com domínio e dados próprios.

## 2. Escopo

### Inclui (v1)
- **Login individual por técnico** (usuário + senha, sessão).
- **Tela do técnico** (mobile / PWA):
  - Posição GPS ao vivo (`watchPosition`).
  - **N = 5 caixas mais próximas**, calculadas **no próprio celular** (haversine em JS).
  - Destaque da caixa mais próxima: nome, distância, descrição.
  - Lista das próximas caixas com distância; tocar foca no mapa.
  - Botão **"Navegar"** → abre Google Maps do celular com rota até a caixa.
  - Mapa Leaflet com marcador "você" + marcadores das caixas.
- **Funcionamento offline / sinal ruim**:
  - Lista de caixas baixada ao logar e guardada no dispositivo (localStorage) com
    data/hora da última atualização.
  - O cálculo da caixa mais próxima roda no cliente → funciona sem 4G.
  - PWA instalável ("adicionar à tela inicial"); service worker cacheia a casca do app.
- **Painel admin com login**:
  - Upload do KML da rede.
  - Ajuste **e persistência** do raio de atendimento.
  - **Gestão de técnicos**: criar, listar, desativar/reativar, remover logins.
- **Deploy independente** (Docker), com **tudo atrás de login** (sem superfície pública).

### Fora de escopo (v1)
- Widget do cliente final (removido nesta cópia).
- Registro de instalações, ocupação de portas, ou edição de caixas pelo técnico.
- Mapas offline (tiles): o **fundo** do mapa pode não carregar sem internet; a
  lista e o cálculo da caixa mais próxima continuam funcionando offline.
- Papéis além de `admin` e `tec`.
- Escolha de app de navegação (Google Maps é o único na v1; Waze fica como
  melhoria futura).

## 3. Arquitetura

Aplicação **Flask** (cópia adaptada do `projeto-viabilidade`), organizada em
módulos e blueprints para o `app.py` não crescer sem controle. Tudo servido pela
mesma origem, atrás de sessão de login — **sem endpoints públicos**.

```
projeto-viabilidade-tecnico/
  app.py                       # cria o app, config, registra os blueprints
  viabilidade/
    __init__.py
    core.py                    # haversine, parse_kml, load_cache/save_cache,
                               #   caixas_mais_proximas(lat, lon, n)
    auth.py                    # store de usuários, hash de senha, sessão,
                               #   decorators @admin_required / @tec_required, seed do admin
    api.py                     # blueprint de dados (JSON, atrás de login)
    admin.py                   # blueprint do painel admin (login + KML + raio + técnicos)
    tec.py                     # blueprint da área do técnico (login + tela principal)
  templates/
    admin_login.html
    admin.html                 # painel (com seção "Técnicos")
    tec_login.html
    tec.html                   # tela principal do técnico
  static/
    tec/
      app.js                   # geolocalização, haversine JS, render lista/mapa, navegar
      tec.css
      manifest.webmanifest
      sw.js                    # service worker (casca offline)
      leaflet/                 # Leaflet servido localmente (sem CDN)
      icons/                   # ícones do PWA
  data/  (volume Docker)
    caixas.kml
    caixas_cache.json
    tecnicos.json              # usuários
    config.json                # raio persistido
  requirements.txt
  Dockerfile
  docker-compose.yml
  README.md
```

## 4. Rotas

| Método | Rota | Proteção | Ação |
|---|---|---|---|
| GET | `/` | — | Redireciona para `/tec` |
| GET/POST | `/tec/login` | — | Login do técnico |
| GET | `/tec/logout` | tec | Encerra sessão |
| GET | `/tec` | tec | Tela principal (serve `tec.html`) |
| GET | `/tec/api/caixas` | tec/admin | Lista completa de caixas (JSON) para cache no cliente |
| GET/POST | `/admin/login` | — | Login do admin |
| GET | `/admin/logout` | admin | Encerra sessão admin |
| GET | `/admin` | admin | Painel (stats, KML, raio, técnicos) |
| POST | `/admin/upload` | admin | Upload/processamento do KML |
| POST | `/admin/raio` | admin | Atualiza **e persiste** o raio (`config.json`) |
| POST | `/admin/tecnicos` | admin | Cria um técnico |
| POST | `/admin/tecnicos/<user>/toggle` | admin | Ativa/desativa um técnico |
| POST | `/admin/tecnicos/<user>/delete` | admin | Remove um técnico |

Rotas sem proteção: apenas as telas/POST de **login** e os **estáticos** do app.

## 5. Modelo de dados

Tudo em `data/` (volume Docker persistente):

- **`caixas.kml`** — enviado pelo admin (mesmo formato do projeto original).
- **`caixas_cache.json`** — derivado do KML: `[{nome, descricao, lat, lon}, ...]`.
- **`tecnicos.json`** — usuários:
  ```json
  {
    "joao":  {"role": "tec",   "nome": "João Silva",     "senha_hash": "...", "ativo": true},
    "admin": {"role": "admin", "nome": "Administrador",  "senha_hash": "..."}
  }
  ```
- **`config.json`** — `{"raio_metros": 200}` (persiste o raio entre restarts).

Senhas nunca são armazenadas em texto puro — sempre `werkzeug.security`
(`generate_password_hash` / `check_password_hash`).

## 6. Fluxo de dados

**Admin:** upload do KML → `parse_kml` → grava `caixas_cache.json`. Ajuste do raio
→ grava `config.json`. Cria técnicos → grava `tecnicos.json`.

**Técnico:** loga → sessão criada → app faz `GET /tec/api/caixas` → guarda a lista
em `localStorage` com timestamp → `watchPosition` fornece a posição → o cliente
calcula as **N mais próximas** por haversine em JS → renderiza destaque + lista +
mapa. Botão "Navegar" abre o Google Maps. Sem sinal, o app usa a lista cacheada e
exibe aviso de "dados de DD/MM HH:MM".

## 7. Segurança

- **`SECRET_KEY`** obrigatória via variável de ambiente; sem o default fraco do
  projeto original. A aplicação recusa subir em produção sem uma chave definida.
- **Sessão** por cookie assinado do Flask, com `HttpOnly`, `Secure` e
  `SameSite=Lax`.
- **Senhas** com hash (werkzeug). Nenhuma rota de dados sem sessão.
- **Admin inicial** semeado no primeiro boot a partir de `ADMIN_USER` /
  `ADMIN_PASS` (obrigatórios no primeiro deploy). Se não estiverem definidos e não
  houver nenhum admin em `tecnicos.json`, o app **não sobe** e registra no log a
  necessidade de definir essas variáveis. Uma vez semeado, `tecnicos.json` é a
  fonte da verdade e as variáveis podem ser removidas.
- **Proteção leve contra brute-force** no login (limite simples de tentativas por
  usuário/IP, com pequeno atraso). Mantida simples na v1.
- **CORS habilitado e configurável** (`flask-cors`): aplicado às rotas de API
  (`/tec/api/*`), com as origens permitidas vindas da variável de ambiente
  `CORS_ORIGINS` (lista separada por vírgula; default `*`). Diferente do
  `CORS(app)` liberado geral do projeto original, aqui dá para restringir a
  origens específicas. **Nota:** como a autenticação é por cookie de sessão,
  acesso cross-origin *com credenciais* exige origens explícitas (não `*`) e
  `supports_credentials=True` — a ser definido em `CORS_ORIGINS` quando esse uso
  existir.

## 8. PWA / offline

- **`manifest.webmanifest`**: nome "Voltec Técnico", ícones, `display: standalone`,
  cor de tema.
- **`sw.js`**: cacheia a casca (HTML da tela do técnico, CSS, JS, Leaflet local,
  ícones). Estratégia: *cache-first* para estáticos; *network-first* com fallback
  ao cache para o HTML.
- **Dados das caixas** em `localStorage` (JSON), não no cache do service worker —
  atualizados quando online, com timestamp exibido na tela.
- **Leaflet servido localmente** (`static/tec/leaflet/`) para não depender de CDN.

## 9. Navegação (deep links)

- **Google Maps** (v1): `https://www.google.com/maps/dir/?api=1&destination=LAT,LON`
  — abre o app nativo de mapas em Android/iOS traçando a rota.
- Waze (`https://waze.com/ul?ll=LAT,LON&navigate=yes`) fica como melhoria futura.

## 10. Deploy

- Novo repositório/pasta `projeto-viabilidade-tecnico` (cópia adaptada — os
  arquivos de código do projeto original são copiados para este repo, sem o
  histórico git do original e sem o widget do cliente).
- **`Dockerfile` / `docker-compose.yml`** próprios; volume próprio para `/app/data`.
- **Servidor WSGI de produção**: troca do flask dev server (`app.run`) por
  **gunicorn**, adequado a um app com login em produção.
- **Proxy reverso via Nginx Proxy Manager (NPM)**, que já roda em produção: o
  deploy apenas expõe a porta do container; no NPM cria-se um **Proxy Host** novo
  para o novo domínio/subdomínio (ex.: `tecnico.voltecautomacao.com.br`) apontando
  para `host:porta` do container, com **TLS/Let's Encrypt** gerenciado pelo próprio
  NPM. Nenhum arquivo `nginx.conf` escrito à mão; **sem** o bloqueio de `text/html`
  — o login já protege tudo. Recomenda-se ativar no Proxy Host: *Websockets
  Support* (não obrigatório) e *Block Common Exploits*.
- **Variáveis de ambiente** (docker-compose): `SECRET_KEY` (obrigatória),
  `ADMIN_USER` / `ADMIN_PASS` (primeiro boot), `RAIO_METROS` (default),
  `CORS_ORIGINS` (default `*`).
- **KML**: o admin faz o upload do mesmo KML nesse app novo (passo manual).

## 11. Correções herdadas do projeto original (aplicar nesta cópia)

- Raio de atendimento **agora persiste** (`config.json`) — no original era um global
  em memória perdido a cada restart.
- Remover **`xmltodict`** (dependência morta; o parsing usa `xml.etree.ElementTree`).
- Manter **`flask-cors`**, porém **configurável por `CORS_ORIGINS`** em vez do
  `CORS(app)` liberado geral (ver Segurança).
- Não copiar o arquivo **`data`** de 0 byte que existe na raiz do original.
- Trocar **flask dev server → gunicorn**.
- Adicionar **autenticação** (o original não tinha nenhuma).

## 12. Testes

- **Unit**
  - `haversine` — distâncias entre pares de coordenadas conhecidos.
  - `parse_kml` — KML de exemplo com `Placemark`/`Point`; nomes, descrições e
    ordem lon,lat corretos.
  - `caixas_mais_proximas(lat, lon, n)` — ordenação por distância e limite N.
  - `auth` — hash/verify de senha; decorators redirecionam/bloqueiam sem sessão.
- **Integração** (Flask test client)
  - Login/logout de admin e de técnico.
  - Rotas protegidas retornam redirect/401 sem sessão.
  - CRUD de técnicos (criar, desativar, remover).
  - `GET /tec/api/caixas` exige sessão e retorna as caixas.
  - `POST /admin/upload` popula o cache; `POST /admin/raio` persiste em `config.json`.
- **Manual** (celular real)
  - Permissão de GPS, posição ao vivo, ordem correta das caixas.
  - Botão "Navegar" abre o app de mapas na rota certa.
  - Teste offline em **modo avião**: a lista e o cálculo funcionam; aviso de dados
    defasados aparece.

## 13. Critérios de sucesso

- O técnico loga no celular e vê a caixa mais próxima com a distância correta, e
  consegue navegar até ela.
- Funciona com sinal ruim (offline) para achar a caixa.
- O admin gerencia KML, raio e técnicos por tela, com login.
- A aplicação em produção permanece intocada.
