#!/usr/bin/env python3
"""
公共配置模板：pom.xml 依赖片段 和 .env 示例配置。
"""


def get_pom_dependency(datasource_type: str) -> str:
    """返回对应数据源的 Maven 依赖片段，注入到 pom.xml 的占位注释处。"""
    dependencies = {
        'mysql': """        <dependency>
            <groupId>mysql</groupId>
            <artifactId>mysql-connector-java</artifactId>
            <version>8.0.33</version>
        </dependency>""",
        'postgresql': """        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <version>42.6.0</version>
        </dependency>""",
        'sqlserver': """        <dependency>
            <groupId>com.microsoft.sqlserver</groupId>
            <artifactId>mssql-jdbc</artifactId>
            <version>12.2.0.jre8</version>
        </dependency>""",
        'oracle': """        <dependency>
            <groupId>com.oracle.database.jdbc</groupId>
            <artifactId>ojdbc8</artifactId>
            <version>21.9.0.0</version>
        </dependency>""",
    }
    return dependencies.get(datasource_type, '')


def get_datasource_config_example(datasource_type: str) -> dict:
    """返回对应数据源的 .env 配置示例。

    key 格式为 datasource.xxx，与 Service 层 @Value("${datasource.xxx}") 对应。
    由 generate_code.py 在生成后端代码时写入 backend/.env 文件。
    开发者需将示例值替换为真实的数据库连接信息。
    """
    configs = {
        'mysql': {
            'datasource.host': 'localhost',
            'datasource.port': '3306',
            'datasource.database': 'mydb',
            'datasource.username': 'root',
            'datasource.password': 'your_password_here',
            'datasource.tableName': 'your_table_name',
            'datasource.sslMode': 'PREFERRED',
        },
        'postgresql': {
            'datasource.host': 'localhost',
            'datasource.port': '5432',
            'datasource.database': 'mydb',
            'datasource.username': 'postgres',
            'datasource.password': 'your_password_here',
            'datasource.tableName': 'your_table_name',
        },
        'sqlserver': {
            'datasource.host': 'localhost',
            'datasource.port': '1433',
            'datasource.database': 'mydb',
            'datasource.username': 'sa',
            'datasource.password': 'your_password_here',
            'datasource.tableName': 'your_table_name',
            'datasource.trustServerCertificate': 'false',
        },
        'oracle': {
            'datasource.host': 'localhost',
            'datasource.port': '1521',
            'datasource.database': 'ORCL',
            'datasource.username': 'system',
            'datasource.password': 'your_password_here',
            'datasource.tableName': 'YOUR_TABLE_NAME',
        },
    }
    return configs.get(datasource_type, configs['mysql'])
