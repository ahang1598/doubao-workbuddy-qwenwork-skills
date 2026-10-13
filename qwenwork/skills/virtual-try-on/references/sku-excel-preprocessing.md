# Excel 预处理（商陆花 / 笑铺日记）

完整流程：**预处理 Excel → 初始化 SKU 多维表 → 提示用户导入数据 → 切换店铺数据源**

---

## 步骤 1：预处理 Excel

对商陆花或笑铺日记导出的 Excel 进行预处理：将相同款号的行合并为一行，条码、颜色、尺码、库存按对应顺序用逗号分隔，其他字段取第一行的值。

```bash
python scripts/merge_sku.py --input "输入文件.xlsx" --output "输出文件.xlsx"
```

- `--input`（必填）：输入 Excel 文件路径
- `--output`（可选）：输出文件路径，默认在输入文件同目录生成 `原文件名_合并.xlsx`

> 表格必须包含「款号」「条码」「颜色」「尺码」「库存」列，否则脚本会报错提示缺少列。

---

## 步骤 2：初始化 SKU 多维表

创建一个用于存储 SKU 数据的多维表（需要用户提供 Base ID）：

```bash
python scripts/create_sku_table.py --base-id <BASE_ID>
```

脚本输出 JSON，包含 `baseId`、`tableId`、`tableUrl`。

> 如果用户没有 Base，先提示用户在钉钉多维表中创建一个 Base，获取 Base ID 后再执行此命令。

---

## 步骤 3：导入数据到多维表

将预处理后的 Excel 数据自动导入步骤 2 创建的多维表：

```bash
python scripts/import_sku_records.py --base-id <BASE_ID> --table-id <TABLE_ID> --input "合并后.xlsx"
```

- `--base-id`（必填）：步骤 2 输出的 Base ID
- `--table-id`（必填）：步骤 2 输出的 Table ID
- `--input`（必填）：步骤 1 生成的合并后 Excel 文件路径

脚本会自动按 schema 做字段类型转换，分批（每批 5 条）写入多维表。

---

## 步骤 4：切换店铺数据源到多维表

导入完成后，使用 sku-source 命令将店铺数据源切换为该多维表：

```bash
python scripts/cli.py try-on sku-source --aitable-url "<多维表链接>"
```

> 多维表链接即步骤 2 输出的 `tableUrl`，或用户在浏览器中打开多维表后地址栏的 URL。
