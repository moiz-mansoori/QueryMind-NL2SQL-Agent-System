import os

def replace_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    content = content.replace('"agents.nodes.AsyncGroq"', '"agents.nodes.utils.AsyncGroq"')
    
    # Specific get_pool replacements
    content = content.replace('@patch("agents.nodes.get_pool")\n@patch("agents.nodes.get_embed_model")\nasync def test_schema_retriever', 
                              '@patch("agents.nodes.retriever.get_pool")\n@patch("agents.nodes.retriever.get_embed_model")\nasync def test_schema_retriever')
    
    content = content.replace('@patch("agents.nodes.get_pool")\nasync def test_sql_executor', 
                              '@patch("agents.nodes.executor.get_pool")\nasync def test_sql_executor')
    
    content = content.replace('@patch("agents.nodes.get_pool")\nasync def test_query_logger', 
                              '@patch("agents.nodes.logger.get_pool")\nasync def test_query_logger')

    with open(filepath, 'w') as f:
        f.write(content)

replace_in_file('../tests/unit/test_nodes.py')
replace_in_file('../tests/unit/test_sql_generator.py')
print('Tests patched successfully.')
