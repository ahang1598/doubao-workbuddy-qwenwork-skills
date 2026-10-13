#!/usr/bin/env python3
"""
AI表格数据源插件开发环境配置脚本
用途：检查本地开发环境，并在显式授权后安装依赖
"""

import shutil
import sys
import argparse
import subprocess
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='配置AI表格数据源插件开发环境')
    parser.add_argument('--name', required=True, help='插件英文标识')
    parser.add_argument('--project-dir', help='项目目录，默认为 {name}-plugin')
    parser.add_argument('--install', action='store_true',
                        help='明确允许执行 pnpm install 和 mvn clean install；默认只检查环境')
    return parser.parse_args()


def check_prerequisites():
    """检查前置条件"""
    print("\n🔍 检查前置条件...")
    
    # 检查 Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        node_version = result.stdout.strip()
        print(f"✓ Node.js: {node_version}")
    except FileNotFoundError:
        print("❌ 未安装 Node.js，请先安装: https://nodejs.org/")
        return False
    
    # 检查 pnpm（新版前端模板使用 pnpm-lock.yaml）
    try:
        result = subprocess.run(['pnpm', '--version'], capture_output=True, text=True)
        pnpm_version = result.stdout.strip()
        print(f"✓ pnpm: {pnpm_version}")
    except FileNotFoundError:
        print("❌ 未安装 pnpm，请先安装: npm install -g pnpm@9")
        return False
    
    # 检查 Java
    try:
        result = subprocess.run(
            ['java', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        java_version = result.stdout.split('\n')[0]
        print(f"✓ Java: {java_version}")
    except FileNotFoundError:
        print("❌ 未安装 Java，请先安装 JDK 8+")
        return False
    
    # 检查 Maven
    try:
        result = subprocess.run(['mvn', '--version'], capture_output=True, text=True)
        maven_version = result.stdout.split('\n')[0]
        print(f"✓ Maven: {maven_version}")
    except FileNotFoundError:
        print("❌ 未安装 Maven，请先安装: https://maven.apache.org/")
        return False
    
    return True


def install_frontend_dependencies(project_dir):
    """安装前端依赖"""
    print("\n📦 安装前端依赖...")
    frontend_dir = project_dir / 'frontend'
    
    if not (frontend_dir / 'package.json').exists():
        print("❌ 未找到 package.json，请先运行 generate_code.py")
        return False
    
    try:
        subprocess.run(['pnpm', 'install'], cwd=frontend_dir, check=True)
        print("✓ 前端依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 前端依赖安装失败: {e}")
        return False


def install_backend_dependencies(project_dir):
    """安装后端依赖"""
    print("\n📦 安装后端依赖...")
    backend_dir = project_dir / 'backend'
    
    if not (backend_dir / 'pom.xml').exists():
        print("❌ 未找到 pom.xml，请先运行 generate_code.py")
        return False
    
    try:
        subprocess.run(['mvn', 'clean', 'install', '-DskipTests'], cwd=backend_dir, check=True)
        print("✓ 后端依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 后端依赖安装失败: {e}")
        return False


def print_tunnel_instructions():
    """打印内网穿透启动说明"""
    print(f"\n🌐 内网穿透配置（推荐 Cloudflare Tunnel）:")
    print(f"   # macOS 安装 cloudflared")
    print(f"   brew install cloudflare/cloudflare/cloudflared")
    print(f"")
    print(f"   # 启动内网穿透")
    print(f"   cloudflared tunnel --url http://localhost:8080")
    print(f"")
    print(f"   详细说明见项目目录下的 docs/debug-guide.md")


def copy_debug_guide(project_dir):
    """将 docs/debug-guide.md 复制到目标项目的 docs/ 目录。
    源文件由仓库统一维护，setup_dev 只负责复制，不在代码里内联文档内容。
    """
    print("\n📖 复制调试指南...")

    scripts_dir = Path(__file__).parent
    source_path = scripts_dir.parent / 'docs' / 'debug-guide.md'

    if not source_path.exists():
        raise FileNotFoundError(
            f"调试指南源文件不存在: {source_path}\n"
            "请确保 docs/debug-guide.md 存在"
        )

    dest_docs_dir = project_dir / 'docs'
    dest_docs_dir.mkdir(exist_ok=True)

    dest_path = dest_docs_dir / 'debug-guide.md'
    shutil.copy2(source_path, dest_path)
    print(f"✓ 复制文件: docs/debug-guide.md")

def print_next_steps(project_dir):
    """打印下一步操作"""
    print(f"\n✅ 开发环境配置完成！")
    print(f"\n📚 下一步操作:")
    print(f"\n1. 启动后端服务:")
    print(f"   cd {project_dir}")
    print(f"   ./scripts/start-backend.sh")
    print(f"\n2. 启动前端服务 (新终端):")
    print(f"   cd {project_dir}")
    print(f"   ./scripts/start-frontend.sh")
    print(f"\n3. 配置内网穿透 (新终端)：")
    print(f"   cloudflared tunnel --url http://localhost:8080")
    print(f"\n4. 在 AI 表格中测试：")
    print(f"   - 使用 Cloudflare Tunnel 提供的公网 URL")
    print(f"   - 参考 docs/debug-guide.md 获取详细调试指南")
    print(f"\n📖 更多信息:")
    print(f"   - 调试指南: {project_dir}/docs/debug-guide.md")
    print(f"   - 项目文档: {project_dir}/README.md")


def main():
    """主函数"""
    args = parse_args()
    
    # 确定项目目录
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = Path(f"{args.name.replace(' ', '-').lower()}-plugin")
    
    # 检查项目目录是否存在
    if not project_dir.exists():
        print(f"❌ 错误: 项目目录 {project_dir} 不存在")
        print(f"请先运行 init_plugin.py 初始化项目")
        sys.exit(1)
    
    print(f"\n🚀 开始配置开发环境...")
    print(f"📁 项目目录: {project_dir.absolute()}\n")
    
    try:
        # 检查前置条件
        if not check_prerequisites():
            print("\n❌ 前置条件检查失败，请先安装必要的工具")
            sys.exit(1)
        
        # Install dependencies only after the caller explicitly opts in.
        if args.install:
            if not install_frontend_dependencies(project_dir):
                print("\n⚠️  前端依赖安装失败，但继续配置其他部分...")
            
            if not install_backend_dependencies(project_dir):
                print("\n⚠️  后端依赖安装失败，但继续配置其他部分...")
        else:
            print("\n⏭️  未提供 --install，跳过依赖安装")
            print("   确认允许联网下载并修改项目后，可添加 --install 重新执行")
        
        # 打印内网穿透说明
        print_tunnel_instructions()

        # 复制调试指南
        copy_debug_guide(project_dir)

        # 打印下一步操作
        print_next_steps(project_dir)
        
    except Exception as e:
        print(f"\n❌ 配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
