# Rotas e navegação

A aplicação usa o `ft.Router` declarativo e a estratégia Web `hash`.

## Execução Web

```powershell
flet run --web --port 8600 src\main.py
```

Ao executar pelo entrypoint Python, a estratégia é definida por:

```python
ft.run(main, route_url_strategy="hash")
```

## URLs

- Dashboard: `/#/`
- Vínculos: `/#/bindings`
- Serviços: `/#/services`
- Relatório detalhado: `/#/dashboard/detail`

A navegação interna continua usando `page.navigate("/rota")`; o Flet converte a rota para a URL Hash no navegador.
