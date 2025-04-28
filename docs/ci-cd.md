# CI/CD Documentation for SentinelIQ

Este documento descreve o processo de Integração Contínua (CI) e Entrega Contínua (CD) configurado para o projeto SentinelIQ.

## Visão Geral

O pipeline de CI/CD do SentinelIQ utiliza o GitHub Actions para automatizar os processos de teste, construção e implantação da aplicação. O pipeline é configurado para:

1. Executar testes e verificações de qualidade de código em todas as branches
2. Construir e publicar imagens Docker para branches principais no GitHub Container Registry
3. Implantar automaticamente apenas em ambiente de produção

## Estrutura do Pipeline

### Pipeline de Desenvolvimento (develop)

O pipeline de desenvolvimento está definido no arquivo `.github/workflows/develop.yml` e consiste em dois jobs principais:

#### 1. Job de Teste (`test`)

Este job é executado em todas as branches e pull requests, e realiza:

- Configuração de serviços necessários (PostgreSQL e Redis)
- Instalação de dependências via Poetry
- Execução de análise estática de código (linting)
- Execução de testes automatizados
- Geração e upload de relatórios de cobertura de código

#### 2. Job de Build de Imagem (`build-image`)

Este job é executado apenas quando há um push para a branch `develop`:

- Configura o Docker Buildx para construção eficiente
- Realiza login no GitHub Container Registry usando o token GITHUB_TOKEN
- Extrai metadados para etiquetas apropriadas
- Constrói e publica as imagens Docker no GHCR com cache otimizado

Observe que o ambiente de desenvolvimento não realiza deploy automático, apenas testes e build de imagem.

### Pipeline de Produção (main)

O pipeline de produção está definido no arquivo `.github/workflows/ci-cd.yml` e adiciona o seguinte job:

#### 3. Job de Implantação (`deploy`)

Este job é executado apenas na branch `main` após a publicação bem-sucedida da imagem:

- Conecta-se ao servidor de produção via SSH
- Atualiza o código fonte
- Implanta a aplicação usando Docker Compose
- Limpa recursos não utilizados

## Configuração necessária

Para configurar corretamente o pipeline de CI/CD, você precisa definir os seguintes segredos no repositório GitHub:

1. Permissões no workflow:
   - As permissões `packages: write` já estão configuradas para permitir o push para o GitHub Container Registry
   - O token `GITHUB_TOKEN` é gerado automaticamente pelo GitHub e usado para autenticação

2. Credenciais do servidor de produção:
   - `PRODUCTION_HOST`: Endereço IP ou hostname do servidor
   - `PRODUCTION_USERNAME`: Nome de usuário para SSH
   - `PRODUCTION_SSH_KEY`: Chave SSH privada para acesso ao servidor

## Script de Implantação Manual

Além do pipeline automatizado, um script de implantação manual está disponível em `scripts/deploy.sh`. Este script pode ser usado para implantações manuais no servidor de produção e realiza as seguintes etapas:

1. Verifica se está sendo executado do diretório raiz do projeto
2. Puxa as últimas alterações do repositório Git
3. Verifica se o arquivo `.env` existe
4. Constrói e inicia os containers Docker
5. Aplica migrações de banco de dados
6. Coleta arquivos estáticos
7. Limpa recursos Docker não utilizados

## Fluxo de Trabalho Recomendado

Para manter um fluxo de trabalho eficiente com este pipeline de CI/CD:

1. Desenvolva em branches de feature
2. Crie Pull Requests para a branch `develop`
3. Teste e valide na branch `develop`
4. Para deployments manuais de teste, use o script de deploy ou execute manualmente os comandos necessários
5. Promova alterações da branch `develop` para `main` via Pull Request
6. O deploy em produção ocorrerá automaticamente após merge na `main`

## Acesso às Imagens no GitHub Container Registry

As imagens Docker estão disponíveis em:
- `ghcr.io/sentineliq/sentineliq:develop` - Branch de desenvolvimento
- `ghcr.io/sentineliq/sentineliq:main` - Branch principal (produção)
- `ghcr.io/sentineliq/sentineliq:sha-xxxxxx` - Versões específicas por commit

## Solução de Problemas

Se você encontrar problemas durante o processo de CI/CD:

1. Verifique os logs de execução no GitHub Actions
2. Confirme se todas as permissões estão configuradas corretamente
3. Verifique a conectividade com o servidor de produção
4. Revise as configurações do Docker e Docker Compose
