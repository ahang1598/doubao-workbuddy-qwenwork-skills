# `design-cli design-asset +get`

读取用户引用的素材资产及其中的条目。本次只支持素材资产。直接使用上下文或服务返回的资产 ID，不拼接、去掉或推断 ID 前缀。

```bash
design-cli design-asset +get --asset-ids ast_123,ast_456
```

`--asset-ids` 必填，支持逗号分隔或重复传入；忽略空项，保留其余 ID 的顺序和值。无需画布 ID，不支持 revision-id。

返回体原样输出，XML 位于 `xml_data`。成功退出 0，业务或网络错误退出 1，参数错误退出 2。只获取详情，不下载全部文件。

```xml
<assets>
  <asset id="ast_123" name="品牌素材">
    <material>
      <description>品牌标志和参考图片</description>
      <items>
        <item item_id="item_456" content_kind="image" name="logo.png" resource_url="https://example.com/drive/file/456"></item>
      </items>
    </material>
  </asset>
</assets>
```

每个资产返回 `id`、`name`、`material.description` 和 `material.items`；每个条目返回 `item_id`、`content_kind`、`name`、`resource_url`。`resource_url` 是云盘文件页，不是媒体下载地址。`content_kind` 为 image、video、audio、document 或 other。XML 由服务端生成。
