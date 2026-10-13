#!/usr/bin/env python3
"""
AI表格数据源插件初始化脚本
用途：创建插件项目的完整目录结构，生成前后端代码，并完成个性化配置
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path

# 导入代码生成函数
sys.path.insert(0, str(Path(__file__).parent))
from generate_code import generate_frontend_code, generate_backend_code


def plugin_slug(value):
    """Validate the stable English identifier used by npm and the plugin manifest."""
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?', value):
        raise argparse.ArgumentTypeError(
            '插件标识只能包含小写字母、数字和连字符，首尾不能是连字符，长度不超过 64 个字符'
        )
    return value


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='初始化AI表格数据源插件项目')
    parser.add_argument('--name', required=True, type=plugin_slug,
                        help='插件英文标识，如：mysql-datasource')
    parser.add_argument('--type', default='custom', 
                       choices=['mysql', 'postgresql', 'sqlserver', 'oracle', 'custom'],
                       help='数据源类型')
    parser.add_argument('--output-dir', help='输出目录，默认为 {name}-plugin')
    return parser.parse_args()


def create_directory_structure(base_dir):
    """创建项目骨架目录。
    frontend/ 和 backend/ 由后续的 generate_frontend_code / generate_backend_code 通过
    copytree 产生，此处只创建它们不会覆盖的辅助目录。
    """
    directories = [
        'scripts',
        'config',
    ]

    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {directory}")


def create_gitignore(base_dir):
    """Protect generated credentials and build artifacts from accidental commits."""
    gitignore = """# Credentials and local configuration
**/.env
**/.env.*
!**/.env.example

# Frontend
**/node_modules/
frontend/build/

# Backend
backend/target/

# IDE and operating-system metadata
.idea/
.vscode/
.DS_Store
"""
    path = base_dir / '.gitignore'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(gitignore)
    print("✓ 创建文件: .gitignore")


def create_frontend_config(base_dir, plugin_name):
    """更新前端配置：读取 generate_frontend_code 已复制到 project_dir/frontend/package.json 的文件，
    将 name 字段替换为当前插件名后写回，其余字段保持不变。
    """
    package_json_path = base_dir / 'frontend' / 'package.json'

    if not package_json_path.exists():
        raise FileNotFoundError(
            f"frontend/package.json 不存在: {package_json_path}\n"
            "请确保 generate_frontend_code 已成功执行"
        )

    with open(package_json_path, 'r', encoding='utf-8') as f:
        package_json = json.load(f)

    # 仅替换 name 字段，其余字段保持 generate_code 复制的模板原样
    package_json['name'] = f"{plugin_name.lower().replace(' ', '-')}-plugin"

    with open(package_json_path, 'w', encoding='utf-8') as f:
        json.dump(package_json, f, indent=2, ensure_ascii=False)
    print("✓ 更新文件: frontend/package.json (name 字段)")


def create_backend_config(base_dir, plugin_name):
    """更新后端配置：读取 generate_backend_code 已复制到 project_dir/backend 的 application.yml，
    将 spring.application.name 替换为当前插件名后写回，其余配置保持不变。
    pom.xml 由 generate_backend_code 复制模板时生成，此处不重复处理。
    """
    yml_path = base_dir / 'backend' / 'src' / 'main' / 'resources' / 'application.yml'

    if not yml_path.exists():
        raise FileNotFoundError(
            f"backend/src/main/resources/application.yml 不存在: {yml_path}\n"
            "请确保 generate_backend_code 已成功执行"
        )

    with open(yml_path, 'r', encoding='utf-8') as f:
        yml_content = f.read()

    # 将模板中的 spring.application.name 替换为当前插件名
    app_name = plugin_name.lower().replace(' ', '-') + '-plugin'
    yml_content = yml_content.replace(
        'name: datasource-plugin',
        f'name: {app_name}'
    )

    with open(yml_path, 'w', encoding='utf-8') as f:
        f.write(yml_content)
    print("✓ 更新文件: backend/src/main/resources/application.yml (spring.application.name 字段)")


def create_plugin_config(base_dir, plugin_name, datasource_type):
    """基于通用模板创建插件配置文件。"""
    template_path = Path(__file__).parent.parent / 'templates' / 'config' / 'plugin.json'
    with open(template_path, 'r', encoding='utf-8') as f:
        plugin_config = json.load(f)

    plugin_config['pluginName'] = plugin_name
    plugin_config['datasourceType'] = datasource_type
    
    with open(base_dir / 'config' / 'plugin.json', 'w', encoding='utf-8') as f:
        json.dump(plugin_config, f, indent=2, ensure_ascii=False)
    print("✓ 创建文件: config/plugin.json")


def create_manifest_config(base_dir, plugin_name):
    """创建符合最新错误码国际化规范的通用 Manifest。"""
    template_path = Path(__file__).parent.parent / 'templates' / 'config' / 'manifest.json'
    with open(template_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    plugin_slug = plugin_name.lower().replace(' ', '-')
    manifest['extensionName'] = plugin_slug
    for locale in manifest.get('i18nName', {}):
        manifest['i18nName'][locale] = plugin_name

    with open(base_dir / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print("✓ 创建文件: manifest.json")

def create_tunnel_guide(base_dir):
    """在 config/ 目录下生成 tunnel-guide.txt，说明如何使用 Cloudflare Tunnel 进行内网穿透。"""
    guide = """# 内网穿透说明

AI 表格服务端需要通过公网调用后端接口，本地调试时需要内网穿透工具。

推荐：Cloudflare Tunnel（无需注册账号）

  # macOS 安装
  brew install cloudflare/cloudflare/cloudflared

  # 启动内网穿透（穿透后端 8080 端口）
  cloudflared tunnel --url http://localhost:8080

详细说明见 docs/debug-guide.md
"""
    guide_path = base_dir / 'config' / 'tunnel-guide.txt'
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide)
    print("✓ 创建文件: config/tunnel-guide.txt (内网穿透说明)")


def create_scripts(base_dir):
    """创建启动和构建脚本。脚本假设从项目根目录执行（即 ./scripts/xxx.sh 的方式调用）。"""
    start_frontend = """#!/bin/bash
# 启动前端开发服务器
# 使用方式：在项目根目录执行 ./scripts/start-frontend.sh

set -e

echo "启动前端开发服务器..."

if [ ! -d "frontend" ]; then
    echo "错误: 未找到 frontend 目录，请在项目根目录下执行本脚本"
    exit 1
fi

cd frontend

if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    pnpm install
fi

echo "当前目录: $(pwd)"
pnpm run dev
"""

    start_backend = """#!/bin/bash
# 启动后端开发服务器
# 使用方式：在项目根目录执行 ./scripts/start-backend.sh

set -e

echo "启动后端开发服务器..."

if [ ! -d "backend" ]; then
    echo "错误: 未找到 backend 目录，请在项目根目录下执行本脚本"
    exit 1
fi

cd backend

echo "当前目录: $(pwd)"
mvn spring-boot:run
"""

    build_script = """#!/bin/bash
# 构建生产版本
# 使用方式：在项目根目录执行 ./scripts/build.sh

set -e

echo "构建前端..."
cd frontend
pnpm run build
cd ..

echo "构建后端..."
cd backend
mvn clean package -DskipTests
cd ..

echo "构建完成！"
echo "前端打包文件: frontend/build/"
echo "后端 JAR 包: backend/target/"
"""

    scripts = {
        'start-frontend.sh': start_frontend,
        'start-backend.sh': start_backend,
        'build.sh': build_script,
    }

    for filename, content in scripts.items():
        script_path = base_dir / 'scripts' / filename
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(script_path, 0o755)
        print(f"✓ 创建脚本: scripts/{filename}")


def create_readme(base_dir, plugin_name, plugin_type):
    """创建 README 文档"""
    readme_content = f"""# {plugin_name} 插件

## 项目简介

这是一个钉钉AI表格数据源连接器插件，用于连接 {plugin_type.upper()} 数据源。

## 项目结构

```
.
├── frontend/          # 前端项目 (React + TypeScript)
├── backend/           # 后端项目 (Java Spring Boot)
├── scripts/           # 启动和构建脚本
└── config/            # 配置文件
```

## 快速开始

### 1. 安装依赖

**前端:**
```bash
cd frontend
pnpm install
```

**后端:**
```bash
cd backend
mvn clean install
```

### 2. 配置

编辑 `backend/src/main/resources/application.yml`，配置你的数据源连接信息和 secretKey。

同时检查根目录 `manifest.json`，替换图标、前端地址、后端地址、隐私协议和服务协议占位值。

### 3. 启动开发服务器

**启动后端（在项目根目录执行）:**
```bash
./scripts/start-backend.sh
```

**启动前端（在项目根目录执行）:**
```bash
./scripts/start-frontend.sh
```

### 4. 配置内网穿透

推荐使用 Cloudflare Tunnel（无需注册账号，一行命令）将后端暴露到公网：

```bash
# macOS 安装 cloudflared
brew install cloudflare/cloudflare/cloudflared

# 启动内网穿透（穿透后端 8080 端口）
cloudflared tunnel --url http://localhost:8080
```

### 5. 在 AI 表格中测试

1. 进入钉钉 AI 表格的数据连接中心
2. 选择“自定义数据源”
3. 填入 Cloudflare Tunnel 提供的公网 URL
4. 测试连接和数据同步

## 开发指南

详细的开发指南请参考：
https://open.dingtalk.com/document/

## 构建生产版本

```bash
./scripts/build.sh
```

构建产物：
- 前端: `frontend/build/`
- 后端: `backend/target/*.jar`

## 技术栈

- **前端**: React 19 + TypeScript + Vite
- **后端**: Java 8 + Spring Boot 2.7
- **构建工具**: Maven + pnpm

## 发布前检查

- 确认 `.env` 和真实密钥未提交到版本控制。
- 确认 `manifest.json` 中不再包含 `your-`、`example.com` 或其他占位值。
- 使用生产配置启动后端，并完成签名验证和端到端同步测试。
"""

    with open(base_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✓ 创建文件: README.md")


def main():
    """主函数"""
    args = parse_args()

    # 确定输出目录
    if args.output_dir:
        base_dir = Path(args.output_dir)
    else:
        base_dir = Path(f"{args.name.replace(' ', '-').lower()}-plugin")

    # 检查关键子目录是否已存在（允许父目录已存在，但不允许覆盖已有的插件内容）
    conflicting_dirs = [
        subdir for subdir in ['frontend', 'backend', 'scripts', 'config']
        if (base_dir / subdir).exists()
    ]
    conflicting_files = [
        filename for filename in ['manifest.json']
        if (base_dir / filename).exists()
    ]
    if conflicting_dirs or conflicting_files:
        conflicts = conflicting_dirs + conflicting_files
        print(f"❌ 错误: 目录 {base_dir} 下已存在以下内容: {', '.join(conflicts)}")
        print("请删除这些目录后重试，或指定一个新的输出目录（--output-dir）")
        sys.exit(1)

    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🚀 开始初始化插件项目: {args.name}")
    print(f"📁 输出目录: {base_dir.absolute()}")
    print(f"📊 数据源类型: {args.type}\n")

    try:
        # 1. 创建辅助目录骨架（scripts/、docs/、config/）
        print("📁 创建目录骨架...")
        create_directory_structure(base_dir)
        create_gitignore(base_dir)

        # 2. 生成前后端代码（copytree templates → frontend/ 和 backend/）
        generate_frontend_code(base_dir)
        generate_backend_code(base_dir, args.type)

        # 3. 在 generate_code 产出的文件基础上做个性化更新
        print("\n⚙️  个性化配置...")
        create_frontend_config(base_dir, args.name)
        create_backend_config(base_dir, args.name)

        # 4. 写入插件元信息配置和内网穿透说明
        create_plugin_config(base_dir, args.name, args.type)
        create_manifest_config(base_dir, args.name)
        create_tunnel_guide(base_dir)

        # 5. 创建启动脚本
        create_scripts(base_dir)

        # 6. 创建 README
        create_readme(base_dir, args.name, args.type)

        print(f"\n✅ 项目初始化完成！")
        print(f"\n下一步:")
        print(f"  1. cd {base_dir}")
        print(f"  2. 编辑 backend/src/main/resources/application.yml，填写数据源连接信息和 secretKey")
        print(f"  3. 运行 ./scripts/start-backend.sh 启动后端")
        print(f"  4. 运行 ./scripts/start-frontend.sh 启动前端")

    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
