import psycopg
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor MCP
mcp = FastMCP("home-services-localdev")

# URL de conexão com o banco de dados
DATABASE_URL = "postgresql://homeservice:HomeService!2026@localhost:5432/home_services_db"


@mcp.tool()
def listar_tabelas() -> str:
    """
    Lista todas as tabelas disponíveis no schema público do banco de dados home_services_db.
    """
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public';
    """
    try:
        # Garantindo modo de leitura até mesmo para listagem
        with psycopg.connect(DATABASE_URL, autocommit=False) as conn:
            conn.execute(
                "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")

            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                if not rows:
                    return "Nenhuma tabela encontrada no schema public."
                return "Tabelas encontradas:\n" + "\n".join(f"- {row[0]}" for row in rows)
    except Exception as e:
        return f"Erro ao listar tabelas: {str(e)}"


@mcp.tool()
def executar_consulta(sql: str) -> str:
    """
    Executa uma consulta SQL (APENAS LEITURA) no banco de dados home_services_db e retorna os resultados.
    Use esta ferramenta APENAS para buscar dados (SELECT). Modificações serão bloqueadas.
    """
    try:
        # Configura a conexão para modo estrito de leitura (impede INSERT, UPDATE, DELETE, DROP, etc)
        with psycopg.connect(DATABASE_URL, autocommit=False) as conn:

            # Trava a transação do banco para aceitar apenas leitura
            conn.execute(
                "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")

            with conn.cursor() as cur:
                cur.execute(sql)

                # Verifica se a consulta retornou colunas (comportamento exclusivo de um SELECT/RETURNING)
                if cur.description:
                    colunas = [desc[0] for desc in cur.description]
                    linhas = cur.fetchall()

                    if not linhas:
                        return "Consulta executada com sucesso. Nenhum registro retornado."

                    # Formata a saída como texto estruturado para a IA ler de forma clara
                    resultado = [" | ".join(
                        colunas), "-" * (len(" | ".join(colunas)))]
                    for linha in linhas:
                        resultado.append(" | ".join(str(val) for val in linha))
                    return "\n".join(resultado)
                else:
                    # Se não retornar colunas, era um comando de modificação que não falhou,
                    # mas nós não fazemos commit e devolvemos um aviso.
                    return "Operação negada: Este MCP está configurado APENAS para consultas (SELECT). Comandos de alteração foram bloqueados."

    except Exception as e:
        # O banco vai disparar um erro automaticamente se um comando de escrita for tentado
        # devido ao "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"
        return f"Erro ao executar consulta (ou tentativa de escrita bloqueada): {str(e)}"


if __name__ == "__main__":
    # Roda o servidor usando Standard I/O (comunicação direta com o Cline)
    mcp.run(transport='stdio')
