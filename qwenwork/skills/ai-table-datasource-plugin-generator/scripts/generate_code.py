#!/usr/bin/env python3
"""
AI表格数据源插件代码生成脚本
用途：生成前后端完整代码（包含配置页面、API接口、签名验证等）
"""

import sys
import json
import shutil
import re
import argparse
from pathlib import Path

# Import failures must be visible; silently falling back would produce an incomplete project.
from datasource_templates import (
    get_mysql_service_impl,
    get_mysql_record_service,
    get_postgresql_service_impl,
    get_postgresql_record_service,
    get_sqlserver_service_impl,
    get_sqlserver_record_service_impl,
    get_oracle_service_impl,
    get_oracle_record_service_impl,
    get_pom_dependency,
    get_datasource_config_example,
)


DATASOURCE_TYPES = ['mysql', 'postgresql', 'sqlserver', 'oracle', 'custom']


def plugin_slug(value):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?', value):
        raise argparse.ArgumentTypeError(
            '插件标识只能包含小写字母、数字和连字符，首尾不能是连字符，长度不超过 64 个字符'
        )
    return value


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成AI表格数据源插件代码')
    parser.add_argument('--name', required=True, type=plugin_slug,
                        help='插件英文标识，如：mysql-datasource')
    parser.add_argument('--project-dir', help='项目目录，默认为 {name}-plugin')
    parser.add_argument('--datasource-type', choices=DATASOURCE_TYPES,
                        help='数据源类型，指定后将更新插件配置并生成对应后端代码')
    parser.add_argument('--with-account-hosting', action='store_true',
                        help='启用三方账号代管：注入 AccountSelector 组件和 CredentialService（与完整代码生成一起使用）')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--account-hosting-only', action='store_true',
                        help='仅注入三方账号代管代码，不重新生成前后端（适用于已在开发中的项目增量开启）')
    modes.add_argument('--frontend-only', action='store_true', help='仅生成前端代码')
    modes.add_argument('--backend-only', action='store_true', help='仅生成后端代码')
    parser.add_argument('--force', action='store_true',
                        help='允许覆盖已有 frontend/backend；使用前必须确认用户已知晓覆盖范围')
    return parser.parse_args()


def load_plugin_config(project_dir):
    """加载插件配置"""
    config_path = project_dir / 'config' / 'plugin.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'type': 'custom'}


def generate_frontend_code(project_dir, plugin_name=None, overwrite=False):
    """生成前端代码：将 templates/frontend 目录复制到项目的 frontend 目录下"""
    print("\n📝 生成前端代码...")

    # 定位 templates/frontend 目录（相对于本脚本所在的 scripts/ 目录）
    scripts_dir = Path(__file__).parent
    templates_frontend_dir = scripts_dir.parent / 'templates' / 'frontend'

    if not templates_frontend_dir.exists():
        raise FileNotFoundError(
            f"模板目录不存在: {templates_frontend_dir}\n"
            "请确保 templates/frontend/ 目录存在且包含前端模板文件"
        )

    dest_dir = project_dir / 'frontend'

    # Existing source is preserved unless the caller explicitly opts in to replacement.
    if dest_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"目标目录已存在: {dest_dir}。如已确认允许覆盖，请重新执行并添加 --force"
            )
        shutil.rmtree(dest_dir)

    shutil.copytree(templates_frontend_dir, dest_dir)

    if plugin_name:
        package_json_path = dest_dir / 'package.json'
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_json = json.load(f)
        package_json['name'] = f"{plugin_name.lower().replace(' ', '-')}-plugin"
        with open(package_json_path, 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2, ensure_ascii=False)

    # 打印复制的文件列表
    for copied_file in sorted(dest_dir.rglob('*')):
        if copied_file.is_file():
            relative_path = copied_file.relative_to(project_dir)
            print(f"✓ 创建文件: {relative_path}")

def inject_account_hosting(project_dir):
    """注入三方账号代管相关代码（幂等，可对已开发项目增量执行）：
    前端：复制 AccountSelector.tsx，并尝试自动修改 App.tsx 以集成账号选择器
    后端：复制 CredentialService.java，并在 application.yml 中追加 encryption-key 占位配置
    """
    print("\n🔐 注入三方账号代管代码...")

    scripts_dir = Path(__file__).parent
    ah_dir = scripts_dir.parent / 'templates' / 'account-hosting'

    if not ah_dir.exists():
        raise FileNotFoundError(
            f"账号代管模板目录不存在: {ah_dir}"
        )

    # ── 前端：复制 AccountSelector.tsx ─────────────────────────────────────
    components_dir = project_dir / 'frontend' / 'src' / 'components'
    components_dir.mkdir(parents=True, exist_ok=True)

    src_component = ah_dir / 'frontend' / 'AccountSelector.tsx'
    dest_component = components_dir / 'AccountSelector.tsx'
    if dest_component.exists():
        print(f"⏭️  跳过（已存在）: frontend/src/components/AccountSelector.tsx")
    else:
        shutil.copy2(src_component, dest_component)
        print(f"✓ 创建文件: frontend/src/components/AccountSelector.tsx")

    # ── 前端：修改 App.tsx 以集成 AccountSelector ──────────────────────────
    app_tsx_path = project_dir / 'frontend' / 'src' / 'App.tsx'
    app_manual_hints = []  # 记录需要手动处理的项

    if app_tsx_path.exists():
        with open(app_tsx_path, 'r', encoding='utf-8') as f:
            app_content = f.read()

        # 如果已经包含 AccountSelector import，说明这个文件已经被注入过
        if "AccountSelector" in app_content:
            print(f"⏭️  App.tsx 已包含 AccountSelector，跳过 App.tsx 修改")
        else:
            original = app_content

            # 1. 在 initView import 后追加 AccountSelector import
            marker1 = "import { initView } from 'dingtalk-docs-cool-app';"
            if marker1 in app_content:
                app_content = app_content.replace(
                    marker1,
                    marker1 + "\nimport AccountSelector from './components/AccountSelector';"
                )
            else:
                app_manual_hints.append(
                    "  手动在 App.tsx 顶部添加: import AccountSelector from './components/AccountSelector';"
                )

            # 2. 在函数内插入 accountId state
            marker2 = "  useEffect(() => {"
            if marker2 in app_content and "accountId" not in app_content:
                app_content = app_content.replace(
                    marker2,
                    "  const [accountId, setAccountId] = useState<string>('');\n\n" + marker2,
                    1
                )
            elif "accountId" not in app_content:
                app_manual_hints.append(
                    "  手动在 App 函数内添加: const [accountId, setAccountId] = useState<string>('');"
                )

            # 3. 在新版表单结构中插入账号选择器
            marker3 = "        {/* ── 示例表单项：下拉选择 ── */}"
            if marker3 in app_content:
                app_content = app_content.replace(
                    marker3,
                    "        <FieldGroup>\n"
                    "          <FieldLabel>选择账号</FieldLabel>\n"
                    "          <AccountSelector onSelect={setAccountId} />\n"
                    "        </FieldGroup>\n\n"
                    + marker3
                )
            else:
                app_manual_hints.append(
                    "  手动在 JSX 内容区插入: <AccountSelector onSelect={setAccountId} />"
                )

            # 4. 将 accountId 绑定到 saveConfigAndGoNext
            marker4 = 'await Dingdocs.base.host.dataSource.saveConfigAndGoNext(config);'
            if marker4 in app_content:
                app_content = app_content.replace(
                    marker4,
                    'await Dingdocs.base.host.dataSource.saveConfigAndGoNext(config, { accountId });'
                )
            else:
                app_manual_hints.append(
                    "  手动将 saveConfigAndGoNext(config) 改为 saveConfigAndGoNext(config, { accountId })"
                )

            if app_content != original:
                with open(app_tsx_path, 'w', encoding='utf-8') as f:
                    f.write(app_content)
                print(f"✓ 更新文件: frontend/src/App.tsx（集成 AccountSelector）")
    else:
        print(f"⚠️  未找到 frontend/src/App.tsx，跳过自动修改")
        app_manual_hints.append("  未找到 App.tsx，请手动将 AccountSelector 集成到你的页面")

    # ── 后端：复制 CredentialService.java ──────────────────────────────────
    service_dir = (
        project_dir / 'backend' / 'src' / 'main' / 'java'
        / 'com' / 'dingtalk' / 'plugin' / 'service'
    )
    service_dir.mkdir(parents=True, exist_ok=True)

    src_service = ah_dir / 'backend' / 'CredentialService.java'
    dest_service = service_dir / 'CredentialService.java'
    if dest_service.exists():
        print(f"⏭️  跳过（已存在）: backend/.../service/CredentialService.java")
    else:
        shutil.copy2(src_service, dest_service)
        print(f"✓ 创建文件: backend/src/main/java/com/dingtalk/plugin/service/CredentialService.java")

    # ── 后端：在 application.yml 追加 encryption-key 占位 ─────────────────
    yml_path = project_dir / 'backend' / 'src' / 'main' / 'resources' / 'application.yml'
    if yml_path.exists():
        with open(yml_path, 'r', encoding='utf-8') as f:
            yml_content = f.read()

        if 'encryption-key' not in yml_content:
            marker = '  enable-signature-verification: false\n'
            encryption_config = (
                "  # 在开放平台配置的 encryptionKey，用于解密 credentialToken（三方账号代管）\n"
                "  # 未配置时 credentialToken 为 Base64url 编码的明文凭证 JSON，直接解码即可（仅适合本地开发）\n"
                "  encryption-key:\n"
            )
            if marker in yml_content:
                yml_content = yml_content.replace(marker, marker + encryption_config, 1)
                with open(yml_path, 'w', encoding='utf-8') as f:
                    f.write(yml_content)
                print(f"✓ 更新文件: backend/src/main/resources/application.yml（追加 encryption-key 占位）")
            else:
                print(f"⚠️  application.yml 未找到 plugin 配置插入点，请手动添加 plugin.encryption-key")
        else:
            print(f"⏭️  application.yml 已包含 encryption-key，跳过")

    # ── 同步更新 plugin.json，补充 encryptionKey 字段 ─────────────────
    plugin_json_path = project_dir / 'config' / 'plugin.json'
    if plugin_json_path.exists():
        with open(plugin_json_path, 'r', encoding='utf-8') as f:
            plugin_cfg = json.load(f)
        if 'encryptionKey' not in plugin_cfg:
            # 将 encryptionKey 插入到 secretKey 之后
            items = list(plugin_cfg.items())
            idx = next((i for i, (k, _) in enumerate(items) if k == 'secretKey'), len(items) - 1)
            items.insert(idx + 1, ('encryptionKey', ''))
            plugin_cfg = dict(items)
            with open(plugin_json_path, 'w', encoding='utf-8') as f:
                json.dump(plugin_cfg, f, indent=2, ensure_ascii=False)
            print(f"✓ 更新文件: config/plugin.json（追加 encryptionKey 占位）")
        else:
            print(f"⏭️  plugin.json 已包含 encryptionKey，跳过")
    
    # ── 在 .prod.yml 中追加 encryption-key 字段 ───────────────
    # 注：模板已包含 encryption-key 字段，此处只对已开发项目做兼容处理
    prod_yml_path = project_dir / 'backend' / 'src' / 'main' / 'resources' / 'application-prod.yml'
    if prod_yml_path.exists():
        with open(prod_yml_path, 'r', encoding='utf-8') as f:
            prod_content = f.read()
        if 'encryption-key' not in prod_content:
            marker = '  enable-signature-verification: true\n'
            encryption_config = (
                "  # 在开放平台配置的 encryptionKey，用于解密 credentialToken（三方账号代管）\n"
                "  encryption-key: ${PLUGIN_ENCRYPTION_KEY:}\n"
            )
            if marker in prod_content:
                prod_content = prod_content.replace(marker, marker + encryption_config, 1)
                with open(prod_yml_path, 'w', encoding='utf-8') as f:
                    f.write(prod_content)
                print(f"✓ 更新文件: backend/src/main/resources/application-prod.yml（追加 encryption-key 字段）")
            else:
                print(f"⚠️  application-prod.yml 未找到 plugin 配置插入点，请手动添加 plugin.encryption-key")
        else:
            print(f"⏭️  application-prod.yml 已包含 encryption-key，跳过")
    
    # ── 汇总输出 ─────────────────────────────────────────────────
    print(f"\n💡 三方账号代管注入完成，后续步骤：")
    print(f"   前端：AccountSelector 中的 credentials 字段默认为 username/password，")
    print(f"         请按实际需求修改 frontend/src/components/AccountSelector.tsx")
    print(f"   后端：如需解密 credentialToken，在 Service 中注入 CredentialService 并调用 decrypt()")
    print(f"")
    print(f"🚨 发布前必备：")
    print(f"   1. 部署时设置环境变量 PLUGIN_SECRET_KEY 和 PLUGIN_ENCRYPTION_KEY")
    print(f"      （PLUGIN_ENCRYPTION_KEY 未配置时，getCredentialToken 返回明文 token，存在安全风险）")
    print(f"   2. 将环境变量和 jar 包放在同一目录，并以 --spring.profiles.active=prod 启动")

    if app_manual_hints:
        print(f"\n⚠️  App.tsx 部分项目需要手动完成（因为文件内容已被修改）：")
        for hint in app_manual_hints:
            print(hint)


def generate_datasource_env(backend_dir, datasource_type):
    """在 backend/ 目录下生成 .env 文件，写入数据库连接示例配置。

    .env 文件使用 Java properties 格式（key=value），由 Spring Boot 通过
    spring.config.import=optional:file:.env[.properties] 加载，
    Service 层通过 @Value("${datasource.xxx}") 注入各字段。

    开发者需将示例值替换为真实的数据库连接信息后再启动服务。
    """
    config = get_datasource_config_example(datasource_type)
    if not config:
        return

    lines = [
        f"# {datasource_type.upper()} 数据库连接配置",
        f"# 请将以下示例值替换为真实的数据库连接信息，然后启动后端服务",
        f"# 注意：.env 文件包含敏感信息，请勿提交到版本控制系统",
        "",
    ]
    for key, value in config.items():
        lines.append(f"{key}={value}")

    env_path = backend_dir / '.env'
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"✓ 已生成 backend/.env ({datasource_type} 数据库连接配置示例)")
    print(f"  ⚠️  请编辑 backend/.env，将示例值替换为真实的数据库连接信息")


def generate_backend_code(project_dir, datasource_type='custom', plugin_name=None, overwrite=False):
    """生成后端代码：复制 templates/backend/java 到 project_dir/backend，
    再根据 datasource_type 替换 pom.xml 依赖、SheetMetaService 和 RecordService。
    """
    print(f"\n📝 生成后端代码 (数据源类型: {datasource_type})...")

    scripts_dir = Path(__file__).parent
    template_dir = scripts_dir.parent / 'templates' / 'backend' / 'java'

    if not template_dir.exists():
        raise FileNotFoundError(
            f"模板目录不存在: {template_dir}\n"
            "请确保 templates/backend/java/ 目录存在且包含后端模板文件"
        )

    dest_dir = project_dir / 'backend'

    # Existing source is preserved unless the caller explicitly opts in to replacement.
    if dest_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"目标目录已存在: {dest_dir}。如已确认允许覆盖，请重新执行并添加 --force"
            )
        shutil.rmtree(dest_dir)

    shutil.copytree(template_dir, dest_dir)

    if plugin_name:
        yml_path = dest_dir / 'src' / 'main' / 'resources' / 'application.yml'
        with open(yml_path, 'r', encoding='utf-8') as f:
            yml_content = f.read()
        app_name = plugin_name.lower().replace(' ', '-') + '-plugin'
        yml_content = yml_content.replace('name: datasource-plugin', f'name: {app_name}', 1)
        with open(yml_path, 'w', encoding='utf-8') as f:
            f.write(yml_content)

    # 打印复制的文件列表
    for copied_file in sorted(dest_dir.rglob('*')):
        if copied_file.is_file():
            relative_path = copied_file.relative_to(project_dir)
            print(f"✓ 创建文件: {relative_path}")

    # custom 类型不需要替换任何内容，模板本身即为示例实现
    if datasource_type == 'custom':
        return

    # ── 1. 生成 backend/.env 文件，注入数据库连接示例配置 ────────────────────
    generate_datasource_env(dest_dir, datasource_type)

    # ── 2. 替换 pom.xml 中的数据库驱动占位注释 ──────────────────────────────
    pom_path = dest_dir / 'pom.xml'
    dependency_snippet = get_pom_dependency(datasource_type)

    if dependency_snippet:
        with open(pom_path, 'r', encoding='utf-8') as f:
            pom_content = f.read()

        placeholder = '<!-- 数据库驱动（可选，根据实际数据源选择） -->'
        if placeholder not in pom_content:
            raise RuntimeError(
                f"pom.xml 中未找到占位注释 '{placeholder}'，无法注入数据库驱动依赖"
            )

        pom_content = pom_content.replace(placeholder, dependency_snippet)

        with open(pom_path, 'w', encoding='utf-8') as f:
            f.write(pom_content)

        print(f"✓ 已将 {datasource_type} 驱动依赖注入 pom.xml")

    # ── 3. 替换 SheetMetaService.java 和 RecordService.java ─────────────────
    service_dir = dest_dir / 'src' / 'main' / 'java' / 'com' / 'dingtalk' / 'plugin' / 'service'

    if datasource_type == 'mysql':
        sheet_meta_content = get_mysql_service_impl()
        record_content = get_mysql_record_service()
    elif datasource_type == 'postgresql':
        sheet_meta_content = get_postgresql_service_impl()
        record_content = get_postgresql_record_service()
    elif datasource_type == 'sqlserver':
        sheet_meta_content = get_sqlserver_service_impl()
        record_content = get_sqlserver_record_service_impl()
    elif datasource_type == 'oracle':
        sheet_meta_content = get_oracle_service_impl()
        record_content = get_oracle_record_service_impl()
    else:
        # custom 等其他类型保留模板中的示例实现，由开发者自行修改
        sheet_meta_content = None
        record_content = None

    if sheet_meta_content:
        sheet_meta_path = service_dir / 'SheetMetaService.java'
        with open(sheet_meta_path, 'w', encoding='utf-8') as f:
            f.write(sheet_meta_content)
        print(f"✓ 已替换 SheetMetaService.java ({datasource_type} 实现)")

    if record_content:
        record_path = service_dir / 'RecordService.java'
        with open(record_path, 'w', encoding='utf-8') as f:
            f.write(record_content)
        print(f"✓ 已替换 RecordService.java ({datasource_type} 实现)")


def update_plugin_config(project_dir, datasource_type):
    """将 datasource_type 写入 plugin.json"""
    config_path = project_dir / 'config' / 'plugin.json'
    if not config_path.exists():
        print(f"⚠️  plugin.json 不存在，跳过配置更新")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config['datasourceType'] = datasource_type

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"✓ 已更新 plugin.json: datasourceType = {datasource_type}")


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

    # 加载插件配置，确定数据源类型
    plugin_config = load_plugin_config(project_dir)
    datasource_type = plugin_config.get('datasourceType', 'custom')

    # 若命令行显式指定了 datasource_type，则以命令行参数为准并写回配置
    if args.datasource_type:
        datasource_type = args.datasource_type
        update_plugin_config(project_dir, datasource_type)

    print(f"\n🚀 开始生成代码...")
    print(f"📁 项目目录: {project_dir.absolute()}")
    print(f"📊 数据源类型: {datasource_type}\n")

    try:
        if args.account_hosting_only:
            # 仅注入账号代管，不重新生成前后端
            inject_account_hosting(project_dir)
        elif args.frontend_only:
            generate_frontend_code(project_dir, args.name, overwrite=args.force)
            if args.with_account_hosting:
                inject_account_hosting(project_dir)
        elif args.backend_only:
            generate_backend_code(project_dir, datasource_type, args.name, overwrite=args.force)
            if args.with_account_hosting:
                inject_account_hosting(project_dir)
        else:
            generate_frontend_code(project_dir, args.name, overwrite=args.force)
            generate_backend_code(project_dir, datasource_type, args.name, overwrite=args.force)
            if args.with_account_hosting:
                inject_account_hosting(project_dir)

        print(f"\n✅ 代码生成完成！")
        print(f"\n下一步:")
        print(f"  1. cd {project_dir}")
        print(f"  2. 运行 setup_dev.py 配置开发环境")
        print(f"  3. 启动前后端服务进行测试")

    except Exception as e:
        print(f"\n❌ 代码生成失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
