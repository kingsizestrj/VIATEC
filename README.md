# Viabilidade — App do Técnico

App dedicado que ajuda técnicos em campo a achar, pelo GPS, as caixas de fibra
mais próximas. Deploy independente da aplicação de produção do widget do cliente.

## Rodar local

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
SECRET_KEY=dev ADMIN_USER=admin ADMIN_PASS=admin123 DATA_DIR=./data COOKIE_SECURE=0 python app.py
```

- Admin: http://localhost:5000/admin/login  (suba o KML, defina o raio, crie técnicos)
- Técnico: http://localhost:5000/tec/login

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

## Deploy (Docker + Nginx Proxy Manager)

```bash
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
export ADMIN_USER=admin
export ADMIN_PASS='uma-senha-forte'
docker compose up -d --build
```

No **Nginx Proxy Manager** (já existente em produção): crie um **Proxy Host**
apontando `tecnico.voltecautomacao.com.br` → `IP_DO_HOST:5001`, ative **SSL**
(Let's Encrypt) e **Block Common Exploits**. Não é necessário nenhum bloqueio de
`text/html` — o login já protege tudo.

## Variáveis de ambiente

| Var | Obrigatória | Default | Descrição |
|---|---|---|---|
| `SECRET_KEY` | sim | — | Chave de sessão do Flask |
| `ADMIN_USER` / `ADMIN_PASS` | 1º boot | — | Cria o admin inicial |
| `RAIO_METROS` | não | 200 | Raio default (ajustável no admin) |
| `CORS_ORIGINS` | não | `*` | Origens permitidas na API (`/tec/api/*`) |
| `DATA_DIR` | não | `/app/data` | Pasta de dados persistentes |

## Uso pelo técnico

1. Abrir a URL no celular e fazer login.
2. "Adicionar à tela inicial" (instala como app).
3. Permitir a localização. A tela mostra a caixa mais próxima, a lista das
   próximas e um mapa; "Navegar" abre o Google Maps.
4. Funciona offline após o primeiro acesso (as caixas ficam salvas no aparelho).
